#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

"""
ObjDecoder parses an object tree from an input stream using
Fantom's serialization format.
"""

from .Token import Token
from .Tokenizer import Tokenizer


class ObjDecoder:
    """Deserializes objects from Fantom serialization format."""

    @staticmethod
    def decode(s):
        """Decode object from string.

        Args:
            s: String to parse

        Returns:
            Decoded object
        """
        from fan.sys.Str import Str
        # Create InStream from string
        in_stream = _StrInStream(s)
        return ObjDecoder(in_stream, None).readObj()

    def __init__(self, in_stream, options=None):
        """Create decoder for input stream.

        Args:
            in_stream: InStream to read from
            options: Optional decode options map
        """
        self.tokenizer = Tokenizer(in_stream)
        self.options = options or {}
        self.usings = []
        self.curt = None
        self._consume()

    def readObj(self):
        """Read an object from the stream.

        Returns:
            Decoded object
        """
        self._readHeader()
        return self._readObj(None, None, True)

    def _readHeader(self):
        """Parse using statements at beginning of stream."""
        while self.curt == Token.USING:
            u = self._readUsing()
            self.usings.append(u)

    def _readUsing(self):
        """Parse using statement."""
        line = self.tokenizer.line
        self._consume()

        pod_name = self._consumeId("Expecting pod name")
        from fan.sys.Pod import Pod
        pod = Pod.find(pod_name, False)
        if pod is None:
            raise self._err(f"Unknown pod: {pod_name}")

        if self.curt != Token.DOUBLE_COLON:
            self._endOfStmt(line)
            return _UsingPod(pod)

        self._consume()
        type_name = self._consumeId("Expecting type name")
        t = pod.type(type_name, False)
        if t is None:
            raise self._err(f"Unknown type: {pod_name}::{type_name}")

        if self.curt == Token.AS:
            self._consume()
            type_name = self._consumeId("Expecting using as name")

        self._endOfStmt(line)
        return _UsingType(t, type_name)

    def _readObj(self, cur_field, peek_type, root):
        """Read object based on current token context.

        Args:
            cur_field: Current field being parsed (for type inference)
            peek_type: Already-peeked type signature
            root: True if this is root object

        Returns:
            Decoded object
        """
        # Literals are standalone
        if Token.isLiteral(self.curt):
            val = self.tokenizer.val
            self._consume()
            return val

        # [ is always list/map collection
        if self.curt == Token.LBRACKET:
            return self._readCollection(cur_field, peek_type)

        # Remaining options must start with type signature
        line = self.tokenizer.line
        t = peek_type if peek_type else self._readType()

        # type(str) = simple
        if self.curt == Token.LPAREN:
            return self._readSimple(line, t)
        # type# = type or slot literal
        elif self.curt == Token.POUND:
            return self._readTypeOrSlotLiteral(line, t)
        # type[ = list/map
        elif self.curt == Token.LBRACKET:
            return self._readCollection(cur_field, t)
        # type or type{ = complex
        else:
            return self._readComplex(line, t, root)

    def _readTypeOrSlotLiteral(self, line, t):
        """Parse type# or type#slot literal."""
        self._consume(Token.POUND, "Expected '#' for type literal")
        if self.curt == Token.ID and not self._isEndOfStmt(line):
            slot_name = self._consumeId("slot literal name")
            return t.slot(slot_name)
        else:
            return t

    def _readSimple(self, line, t):
        """Parse simple type: type(str)"""
        # Parse type(str)
        self._consume(Token.LPAREN, "Expected ( in simple")
        s = self._consumeStr("Expected string literal for simple")
        self._consume(Token.RPAREN, "Expected ) in simple")

        # Look up fromStr method
        m = t.method("fromStr", False)
        if m is None:
            raise self._err(f"Missing method: {t.qname()}.fromStr", line)

        # Invoke fromStr
        try:
            return m.call(s)
        except Exception as e:
            from fan.sys.Err import ParseErr
            raise ParseErr.make(f"{e} [Line {line}]")

    def _readComplex(self, line, t, root):
        """Parse complex type with fields."""
        from fan.sys.Map import Map
        from fan.sys.List import List
        from fan.sys.Type import Type

        to_set = {}  # field -> value
        to_add = []  # collection items

        # Read fields/collection
        self._readComplexFields(t, to_set, to_add)

        # Get make constructor
        make_ctor = t.method("make", False)
        if make_ctor is None:
            raise self._err(f"Missing public constructor {t.qname()}.make", line)

        # Get make args from options
        args = None
        if root and self.options and "makeArgs" in self.options:
            args = list(self.options["makeArgs"])

        # Construct object
        try:
            if args:
                obj = make_ctor.callList(args)
            else:
                obj = make_ctor.call()
        except Exception as e:
            raise self._err(f"Cannot make {t}: {e}", line)

        # Set fields
        for field, val in to_set.items():
            self._complexSet(obj, field, val, line)

        # Add collection items
        if to_add:
            add_method = t.method("add", False)
            if add_method is None:
                raise self._err(f"Method not found: {t.qname()}.add", line)
            for val in to_add:
                self._complexAdd(t, obj, add_method, val, line)

        return obj

    def _readComplexFields(self, t, to_set, to_add):
        """Parse fields and collection items inside { }."""
        if self.curt != Token.LBRACE:
            return
        self._consume()

        while self.curt != Token.RBRACE:
            line = self.tokenizer.line
            read_field = False

            if self.curt == Token.ID:
                name = self._consumeId("Expected field name")
                if self.curt == Token.EQ:
                    self._consume()
                    self._readComplexSet(t, line, name, to_set)
                    read_field = True
                else:
                    # Pushback - reset to start of collection item
                    self.tokenizer.undo(self.tokenizer.type, self.tokenizer.val, self.tokenizer.line)
                    self.curt = self.tokenizer.reset(Token.ID, name, line)

            if not read_field:
                self._readComplexAdd(t, line, to_add)

            if self.curt == Token.COMMA:
                self._consume()
            else:
                self._endOfStmt(line)

        self._consume(Token.RBRACE, "Expected '}'")

    def _readComplexSet(self, t, line, name, to_set):
        """Read field value assignment."""
        field = t.field(name, False)
        if field is None:
            raise self._err(f"Field not found: {t.qname()}.{name}", line)

        val = self._readObj(field, None, False)

        # Make const if needed
        if field.isConst():
            from fan.sys.OpUtil import OpUtil
            try:
                val = OpUtil.toImmutable(val)
            except Exception as e:
                raise self._err(f"Cannot make object const for {field.qname()}: {e}", line)

        to_set[field] = val

    def _complexSet(self, obj, field, val, line):
        """Set field value on object."""
        try:
            field.set(obj, val)
        except Exception as e:
            raise self._err(f"Cannot set field {field.qname()}: {e}", line)

    def _readComplexAdd(self, t, line, to_add):
        """Read collection item to add."""
        val = self._readObj(None, None, False)
        to_add.append(val)

    def _complexAdd(self, t, obj, add_method, val, line):
        """Add collection item to object."""
        try:
            add_method.call(obj, val)
        except Exception as e:
            raise self._err(f"Cannot call {t.qname()}.add: {e}", line)

    def _readCollection(self, cur_field, t):
        """Parse list or map collection."""
        self._consume(Token.LBRACKET, "Expecting '['")

        # Check for type signature
        peek_type = None
        if self.curt == Token.ID and t is None:
            peek_type = self._readType(True)

            # [mapType] is explicit map signature
            if self.curt == Token.RBRACKET and peek_type is not None:
                from fan.sys.Type import Type
                if hasattr(peek_type, 'isMap') and peek_type.isMap():
                    t = peek_type
                    peek_type = None
                    self._consume()
                    while self.curt == Token.LRBRACKET:
                        self._consume()
                        t = t.toListOf()
                    if self.curt == Token.QUESTION:
                        self._consume()
                        t = t.toNullable()
                    if self.curt == Token.POUND:
                        self._consume()
                        return t
                    self._consume(Token.LBRACKET, "Expecting '['")

        # Handle [,] empty list
        if self.curt == Token.COMMA and peek_type is None:
            self._consume()
            self._consume(Token.RBRACKET, "Expecting ']'")
            from fan.sys.List import List
            of_type = self._toListOfType(t, cur_field, False)
            return List.make(of_type)

        # Handle [:] empty map
        if self.curt == Token.COLON and peek_type is None:
            self._consume()
            self._consume(Token.RBRACKET, "Expecting ']'")
            from fan.sys.Map import Map
            map_type = self._toMapType(t, cur_field, False)
            return Map.make(map_type)

        # Read first item
        first = self._readObj(None, peek_type, False)

        # Distinguish list vs map
        if self.curt == Token.COLON:
            return self._readMap(self._toMapType(t, cur_field, True), first)
        else:
            return self._readList(self._toListOfType(t, cur_field, True), first)

    def _readList(self, of_type, first):
        """Parse list: [item, item, ...]"""
        items = [first]

        while self.curt != Token.RBRACKET:
            self._consume(Token.COMMA, "Expected ','")
            if self.curt == Token.RBRACKET:
                break
            items.append(self._readObj(None, None, False))

        self._consume(Token.RBRACKET, "Expected ']'")

        # Infer type if needed
        if of_type is None:
            of_type = self._inferType(items)

        from fan.sys.List import List
        return List.make(of_type, items)

    def _readMap(self, map_type, first_key):
        """Parse map: [key:val, key:val, ...]"""
        items = []  # List of (key, val) pairs

        # Finish first pair
        self._consume(Token.COLON, "Expected ':'")
        items.append((first_key, self._readObj(None, None, False)))

        while self.curt != Token.RBRACKET:
            self._consume(Token.COMMA, "Expected ','")
            if self.curt == Token.RBRACKET:
                break
            key = self._readObj(None, None, False)
            self._consume(Token.COLON, "Expected ':'")
            val = self._readObj(None, None, False)
            items.append((key, val))

        self._consume(Token.RBRACKET, "Expected ']'")

        # Infer type if needed
        if map_type is None:
            keys = [k for k, v in items]
            vals = [v for k, v in items]
            map_type = self._inferMapType({k: v for k, v in items})

        # Create map and populate it
        from fan.sys.Map import Map
        m = Map.make(map_type)
        for key, val in items:
            m.set(key, val)
        return m

    def _toListOfType(self, t, cur_field, infer):
        """Determine list element type."""
        if t is not None:
            return t
        if cur_field is not None:
            ft = cur_field.type()
            if hasattr(ft, 'toNonNullable'):
                ft = ft.toNonNullable()
            if hasattr(ft, 'v'):
                return ft.v()
        if infer:
            return None
        from fan.sys.Type import Type
        return Type.find("sys::Obj").toNullable()

    def _toMapType(self, t, cur_field, infer):
        """Determine map type."""
        if t is not None and hasattr(t, 'isMap') and t.isMap():
            return t
        if cur_field is not None:
            ft = cur_field.type()
            if hasattr(ft, 'toNonNullable'):
                ft = ft.toNonNullable()
            if hasattr(ft, 'isMap') and ft.isMap():
                return ft
        if infer:
            return None
        from fan.sys.Type import Type
        return Type.find("[sys::Obj:sys::Obj?]")

    def _inferType(self, items):
        """Infer common type from list of items."""
        from fan.sys.Type import Type
        if not items:
            return Type.find("sys::Obj").toNullable()
        # Simple: use first item's type
        first = items[0]
        if first is None:
            return Type.find("sys::Obj").toNullable()
        if hasattr(first, 'typeof'):
            return first.typeof()
        # Python primitives
        if isinstance(first, bool):
            return Type.find("sys::Bool")
        if isinstance(first, int):
            return Type.find("sys::Int")
        if isinstance(first, float):
            return Type.find("sys::Float")
        if isinstance(first, str):
            return Type.find("sys::Str")
        return Type.find("sys::Obj")

    def _inferMapType(self, items):
        """Infer map type from key/value items."""
        from fan.sys.Type import Type
        if not items:
            return Type.find("[sys::Obj:sys::Obj?]")
        keys = list(items.keys())
        vals = list(items.values())
        k_type = self._inferType(keys)
        v_type = self._inferType(vals)
        return Type.find(f"[{k_type.signature()}:{v_type.signature()}]")

    def _readType(self, lbracket=False):
        """Parse type signature."""
        t = self._readSimpleType(lbracket)

        if self.curt == Token.QUESTION:
            self._consume()
            t = t.toNullable()

        if self.curt == Token.COLON:
            self._consume()
            lbracket2 = self.curt == Token.LBRACKET
            if lbracket2:
                self._consume()
            from fan.sys.Type import Type
            t = Type.find(f"[{t.signature()}:{self._readType(lbracket2).signature()}]")
            if lbracket2:
                self._consume(Token.RBRACKET, "Expected closing ]")

        while self.curt == Token.LRBRACKET:
            self._consume()
            t = t.toListOf()

        if self.curt == Token.QUESTION:
            self._consume()
            t = t.toNullable()

        return t

    def _readSimpleType(self, lbracket):
        """Parse simple type: [pod::]type"""
        line = self.tokenizer.line
        n = self._consumeId("Expected type signature")

        # Check for using-imported name first
        if self.curt != Token.DOUBLE_COLON:
            for u in self.usings:
                t = u.resolve(n)
                if t is not None:
                    return t
            raise self._err(f"Unresolved type name: {n}")

        # Fully qualified: pod::type
        self._consume(Token.DOUBLE_COLON, "Expected ::")
        type_name = self._consumeId("Expected type name")

        from fan.sys.Pod import Pod
        from fan.sys.Type import Type

        pod = Pod.find(n, False)
        if pod is None:
            raise self._err(f"Pod not found: {n}", line)

        t = pod.type(type_name, False)
        if t is None:
            raise self._err(f"Type not found: {n}::{type_name}", line)

        return t

    def _consumeId(self, expected):
        """Consume identifier token."""
        self._verify(Token.ID, expected)
        id_val = self.tokenizer.val
        self._consume()
        return id_val

    def _consumeStr(self, expected):
        """Consume string literal token."""
        self._verify(Token.STR_LITERAL, expected)
        s = self.tokenizer.val
        self._consume()
        return s

    def _consume(self, token_type=None, expected=None):
        """Consume current token, optionally verifying type."""
        if token_type is not None:
            self._verify(token_type, expected)
        self.curt = self.tokenizer.next()

    def _verify(self, token_type, expected):
        """Verify current token type."""
        if self.curt != token_type:
            raise self._err(f"{expected}, not '{Token.toString(self.curt)}'")

    def _isEndOfStmt(self, last_line):
        """Check if current token ends a statement."""
        if self.curt == Token.EOF:
            return True
        if self.curt == Token.SEMICOLON:
            return True
        return last_line < self.tokenizer.line

    def _endOfStmt(self, last_line):
        """Verify end of statement."""
        if self.curt == Token.EOF:
            return
        if self.curt == Token.SEMICOLON:
            self._consume()
            return
        if last_line < self.tokenizer.line:
            return
        if self.curt == Token.RBRACE:
            return
        raise self._err(f"Expected end of statement; not '{Token.toString(self.curt)}'")

    def _err(self, msg, line=None):
        """Create error with line context."""
        from fan.sys.Err import IOErr
        if line is None:
            line = self.tokenizer.line
        return IOErr.make(f"{msg} [Line {line}]")


class _StrInStream:
    """Simple string-based InStream for decode()."""

    def __init__(self, text):
        self.text = text
        self.pos = 0

    def rChar(self):
        if self.pos >= len(self.text):
            return None
        c = ord(self.text[self.pos])
        self.pos += 1
        return c


class _UsingPod:
    """Using import for entire pod."""

    def __init__(self, pod):
        self.pod = pod

    def resolve(self, name):
        return self.pod.type(name, False)


class _UsingType:
    """Using import for specific type with optional alias."""

    def __init__(self, type_, name):
        self.type = type_
        self.name = name

    def resolve(self, name):
        return self.type if self.name == name else None
