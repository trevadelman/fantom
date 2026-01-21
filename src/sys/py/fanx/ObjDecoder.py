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
        return ObjDecoder(in_stream, None).read_obj()

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

    def read_obj(self):
        """Read an object from the stream.

        Returns:
            Decoded object
        """
        self._read_header()
        return self._read_obj(None, None, True)

    def _read_header(self):
        """Parse using statements at beginning of stream."""
        while self.curt == Token.USING:
            u = self._read_using()
            self.usings.append(u)

    def _read_using(self):
        """Parse using statement."""
        line = self.tokenizer.line
        self._consume()

        pod_name = self._consume_id("Expecting pod name")
        from fan.sys.Pod import Pod
        pod = Pod.find(pod_name, False)
        if pod is None:
            raise self._err(f"Unknown pod: {pod_name}")

        if self.curt != Token.DOUBLE_COLON:
            self._end_of_stmt(line)
            return _UsingPod(pod)

        self._consume()
        type_name = self._consume_id("Expecting type name")
        t = pod.type(type_name, False)
        if t is None:
            raise self._err(f"Unknown type: {pod_name}::{type_name}")

        if self.curt == Token.AS:
            self._consume()
            type_name = self._consume_id("Expecting using as name")

        self._end_of_stmt(line)
        return _UsingType(t, type_name)

    def _read_obj(self, cur_field, peek_type, root):
        """Read object based on current token context.

        Args:
            cur_field: Current field being parsed (for type inference)
            peek_type: Already-peeked type signature
            root: True if this is root object

        Returns:
            Decoded object
        """
        # Literals are standalone
        if Token.is_literal(self.curt):
            val = self.tokenizer.val
            self._consume()
            return val

        # [ is always list/map collection
        if self.curt == Token.LBRACKET:
            return self._read_collection(cur_field, peek_type)

        # Remaining options must start with type signature
        line = self.tokenizer.line
        t = peek_type if peek_type else self._read_type()

        # type(str) = simple
        if self.curt == Token.LPAREN:
            return self._read_simple(line, t)
        # type# = type or slot literal
        elif self.curt == Token.POUND:
            return self._read_type_or_slot_literal(line, t)
        # type[ = list/map
        elif self.curt == Token.LBRACKET:
            return self._read_collection(cur_field, t)
        # type or type{ = complex
        else:
            return self._read_complex(line, t, root)

    def _read_type_or_slot_literal(self, line, t):
        """Parse type# or type#slot literal."""
        self._consume(Token.POUND, "Expected '#' for type literal")
        if self.curt == Token.ID and not self._is_end_of_stmt(line):
            slot_name = self._consume_id("slot literal name")
            return t.slot(slot_name)
        else:
            return t

    def _read_simple(self, line, t):
        """Parse simple type: type(str)"""
        # Parse type(str)
        self._consume(Token.LPAREN, "Expected ( in simple")
        s = self._consume_str("Expected string literal for simple")
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

    def _read_complex(self, line, t, root):
        """Parse complex type with fields."""
        from fan.sys.Map import Map
        from fan.sys.List import List
        from fan.sys.Type import Type

        to_set = {}  # field -> value
        to_add = []  # collection items

        # Read fields/collection
        self._read_complex_fields(t, to_set, to_add)

        # Handle special case of sys::Map
        if t.qname() == "sys::Map":
            # Return empty map since we don't have type params here
            m = Map()
            for field, val in to_set.items():
                self._complex_set(m, field, val, line)
            return m

        # Handle special case of sys::List
        if t.qname() == "sys::List":
            lst = List.make(Type.find("sys::Obj?"))
            for field, val in to_set.items():
                self._complex_set(lst, field, val, line)
            return lst

        # Get make constructor
        make_ctor = t.method("make", False)
        if make_ctor is None:
            raise self._err(f"Missing public constructor {t.qname()}.make", line)

        # Get make args from options
        args = None
        if root and self.options and "makeArgs" in self.options:
            args = list(self.options["makeArgs"])

        # Check if last parameter is a Func (it-block pattern)
        # If so, create a synthetic it-block function from to_set fields
        set_after_ctor = True
        ctor_params = make_ctor.params()
        if ctor_params:
            # Get last param - handle both list and Fantom List
            if hasattr(ctor_params, 'last') and callable(ctor_params.last):
                last_param = ctor_params.last()
            elif hasattr(ctor_params, '__len__') and len(ctor_params) > 0:
                last_param = ctor_params[-1]
            else:
                last_param = None

            if last_param is not None:
                # Get param type
                param_type = last_param.type_() if hasattr(last_param, 'type_') else None
                if param_type is None and hasattr(last_param, 'type'):
                    param_type = last_param.type() if callable(last_param.type) else last_param.type

                # Check if last param fits Func and type is const
                func_type = Type.find("sys::Func")
                if param_type is not None and param_type.fits(func_type) and t.is_const():
                    # Create it-block function from to_set fields
                    from fan.sys.Field import Field
                    it_block = Field.make_set_func(to_set)
                    if args is None:
                        args = []
                    args.append(it_block)
                    set_after_ctor = False

        # Construct object
        try:
            if args:
                obj = make_ctor.call_list(args)
            else:
                obj = make_ctor.call()
        except Exception as e:
            raise self._err(f"Cannot make {t}: {e}", line)

        # Set fields (if not passed to ctor as it-block)
        if set_after_ctor:
            for field, val in to_set.items():
                self._complex_set(obj, field, val, line)

        # Add collection items
        if to_add:
            add_method = t.method("add", False)
            if add_method is None:
                raise self._err(f"Method not found: {t.qname()}.add", line)
            for val in to_add:
                self._complex_add(t, obj, add_method, val, line)

        return obj

    def _read_complex_fields(self, t, to_set, to_add):
        """Parse fields and collection items inside { }."""
        if self.curt != Token.LBRACE:
            return
        self._consume()

        while self.curt != Token.RBRACE:
            line = self.tokenizer.line
            read_field = False

            if self.curt == Token.ID:
                name = self._consume_id("Expected field name")
                if self.curt == Token.EQ:
                    self._consume()
                    self._read_complex_set(t, line, name, to_set)
                    read_field = True
                else:
                    # Pushback - reset to start of collection item
                    self.tokenizer.undo(self.tokenizer.type, self.tokenizer.val, self.tokenizer.line)
                    self.curt = self.tokenizer.reset(Token.ID, name, line)

            if not read_field:
                self._read_complex_add(t, line, to_add)

            if self.curt == Token.COMMA:
                self._consume()
            else:
                self._end_of_stmt(line)

        self._consume(Token.RBRACE, "Expected '}'")

    def _read_complex_set(self, t, line, name, to_set):
        """Read field value assignment."""
        field = t.field(name, False)
        if field is None:
            raise self._err(f"Field not found: {t.qname()}.{name}", line)

        val = self._read_obj(field, None, False)

        # Make const if needed
        if field.is_const():
            from fan.sys.ObjUtil import ObjUtil
            try:
                val = ObjUtil.to_immutable(val)
            except Exception as e:
                raise self._err(f"Cannot make object const for {field.qname()}: {e}", line)

        to_set[field] = val

    def _complex_set(self, obj, field, val, line):
        """Set field value on object."""
        try:
            # Pass check_const=False - during deserialization we can set const fields
            # (like JS: field.set_(obj, val, false))
            if field.is_const():
                from fan.sys.ObjUtil import ObjUtil
                field.set_(obj, ObjUtil.to_immutable(val), check_const=False)
            else:
                field.set_(obj, val)
        except Exception as e:
            raise self._err(f"Cannot set field {field.qname()}: {e}", line)

    def _read_complex_add(self, t, line, to_add):
        """Read collection item to add."""
        val = self._read_obj(None, None, False)
        to_add.append(val)

    def _complex_add(self, t, obj, add_method, val, line):
        """Add collection item to object."""
        try:
            add_method.call(obj, val)
        except Exception as e:
            raise self._err(f"Cannot call {t.qname()}.add: {e}", line)

    def _read_collection(self, cur_field, t):
        """Parse list or map collection."""
        self._consume(Token.LBRACKET, "Expecting '['")

        # Check for type signature
        peek_type = None
        if self.curt == Token.ID and t is None:
            peek_type = self._read_type(True)

            # [mapType] is explicit map signature
            if self.curt == Token.RBRACKET and peek_type is not None:
                from fan.sys.Type import Type, MapType
                if isinstance(peek_type, MapType):
                    t = peek_type
                    peek_type = None
                    self._consume()
                    while self.curt == Token.LRBRACKET:
                        self._consume()
                        t = t.to_list_of()
                    if self.curt == Token.QUESTION:
                        self._consume()
                        t = t.to_nullable()
                    if self.curt == Token.POUND:
                        self._consume()
                        return t
                    self._consume(Token.LBRACKET, "Expecting '['")

        # Handle [,] empty list
        if self.curt == Token.COMMA and peek_type is None:
            self._consume()
            self._consume(Token.RBRACKET, "Expecting ']'")
            from fan.sys.List import List
            of_type = self._to_list_of_type(t, cur_field, False)
            return List.make(of_type)

        # Handle [:] empty map
        if self.curt == Token.COLON and peek_type is None:
            self._consume()
            self._consume(Token.RBRACKET, "Expecting ']'")
            from fan.sys.Map import Map
            map_type = self._to_map_type(t, cur_field, False)
            return Map.make(map_type)

        # Read first item
        first = self._read_obj(None, peek_type, False)

        # Distinguish list vs map
        if self.curt == Token.COLON:
            return self._read_map(self._to_map_type(t, cur_field, True), first)
        else:
            return self._read_list(self._to_list_of_type(t, cur_field, True), first)

    def _read_list(self, of_type, first):
        """Parse list: [item, item, ...]"""
        items = [first]

        while self.curt != Token.RBRACKET:
            self._consume(Token.COMMA, "Expected ','")
            if self.curt == Token.RBRACKET:
                break
            items.append(self._read_obj(None, None, False))

        self._consume(Token.RBRACKET, "Expected ']'")

        # Infer type if needed
        if of_type is None:
            of_type = self._infer_type(items)

        from fan.sys.List import List
        return List.make(of_type, items)

    def _read_map(self, map_type, first_key):
        """Parse map: [key:val, key:val, ...]"""
        items = []  # List of (key, val) pairs

        # Finish first pair
        self._consume(Token.COLON, "Expected ':'")
        items.append((first_key, self._read_obj(None, None, False)))

        while self.curt != Token.RBRACKET:
            self._consume(Token.COMMA, "Expected ','")
            if self.curt == Token.RBRACKET:
                break
            key = self._read_obj(None, None, False)
            self._consume(Token.COLON, "Expected ':'")
            val = self._read_obj(None, None, False)
            items.append((key, val))

        self._consume(Token.RBRACKET, "Expected ']'")

        # Infer type if needed
        if map_type is None:
            keys = [k for k, v in items]
            vals = [v for k, v in items]
            map_type = self._infer_map_type({k: v for k, v in items})

        # Create map and populate it
        from fan.sys.Map import Map
        m = Map.make(map_type)
        for key, val in items:
            m.set_(key, val)
        return m

    def _to_list_of_type(self, t, cur_field, infer):
        """Determine list element type."""
        if t is not None:
            return t
        if cur_field is not None:
            ft = cur_field.type()
            if hasattr(ft, 'to_non_nullable'):
                ft = ft.to_non_nullable()
            if hasattr(ft, 'v'):
                return ft.v  # Property access, not method call (like JS: ft.v)
        if infer:
            return None
        from fan.sys.Type import Type
        return Type.find("sys::Obj").to_nullable()

    def _to_map_type(self, t, cur_field, infer):
        """Determine map type."""
        from fan.sys.Type import Type, MapType
        if t is not None and isinstance(t, MapType):
            return t
        if cur_field is not None:
            ft = cur_field.type()
            if hasattr(ft, 'to_non_nullable'):
                ft = ft.to_non_nullable()
            if isinstance(ft, MapType):
                return ft
        if infer:
            return None
        return Type.find("[sys::Obj:sys::Obj?]")

    def _infer_type(self, items):
        """Infer common type from list of items."""
        from fan.sys.Type import Type
        if not items:
            return Type.find("sys::Obj").to_nullable()

        # Get type of each item, tracking if any nulls present
        types = []
        has_null = False
        for item in items:
            if item is None:
                has_null = True
            elif hasattr(item, 'typeof'):
                types.append(item.typeof())
            elif isinstance(item, bool):
                types.append(Type.find("sys::Bool"))
            elif isinstance(item, int):
                types.append(Type.find("sys::Int"))
            elif isinstance(item, float):
                types.append(Type.find("sys::Float"))
            elif isinstance(item, str):
                types.append(Type.find("sys::Str"))
            else:
                types.append(Type.find("sys::Obj"))

        # If only nulls, return Obj?
        if not types:
            return Type.find("sys::Obj").to_nullable()

        # Get unique non-nullable signatures
        sigs = set(t.to_non_nullable().signature() if hasattr(t, 'to_non_nullable') else t.signature() for t in types)

        # If all types are the same
        if len(sigs) == 1:
            base_type = types[0]
            if hasattr(base_type, 'to_non_nullable'):
                base_type = base_type.to_non_nullable()
            return base_type.to_nullable() if has_null else base_type

        # Find common base type for numeric types (Int/Float -> Num)
        if sigs <= {"sys::Int", "sys::Float"}:
            return Type.find("sys::Num").to_nullable() if has_null else Type.find("sys::Num")

        # Check if all types have a common non-Obj base (e.g., subclasses)
        # For now, fall back to Obj? for mixed non-numeric types
        return Type.find("sys::Obj").to_nullable()

    def _infer_map_type(self, items):
        """Infer map type from key/value items."""
        from fan.sys.Type import Type
        if not items:
            return Type.find("[sys::Obj:sys::Obj?]")
        keys = list(items.keys())
        vals = list(items.values())
        k_type = self._infer_type(keys)
        v_type = self._infer_type(vals)
        return Type.find(f"[{k_type.signature()}:{v_type.signature()}]")

    def _read_type(self, lbracket=False):
        """Parse type signature."""
        t = self._read_simple_type(lbracket)

        if self.curt == Token.QUESTION:
            self._consume()
            t = t.to_nullable()

        if self.curt == Token.COLON:
            self._consume()
            lbracket2 = self.curt == Token.LBRACKET
            if lbracket2:
                self._consume()
            from fan.sys.Type import Type
            t = Type.find(f"[{t.signature()}:{self._read_type(lbracket2).signature()}]")
            if lbracket2:
                self._consume(Token.RBRACKET, "Expected closing ]")

        while self.curt == Token.LRBRACKET:
            self._consume()
            t = t.to_list_of()

        if self.curt == Token.QUESTION:
            self._consume()
            t = t.to_nullable()

        return t

    def _read_simple_type(self, lbracket):
        """Parse simple type: [pod::]type"""
        line = self.tokenizer.line
        n = self._consume_id("Expected type signature")

        # Check for using-imported name first
        if self.curt != Token.DOUBLE_COLON:
            for u in self.usings:
                t = u.resolve(n)
                if t is not None:
                    return t
            raise self._err(f"Unresolved type name: {n}")

        # Fully qualified: pod::type
        self._consume(Token.DOUBLE_COLON, "Expected ::")
        type_name = self._consume_id("Expected type name")

        from fan.sys.Type import Type

        # Use Type.find() directly - it handles all type lookup including sys types
        t = Type.find(f"{n}::{type_name}", False)
        if t is None:
            raise self._err(f"Type not found: {n}::{type_name}", line)

        return t

    def _consume_id(self, expected):
        """Consume identifier token."""
        self._verify(Token.ID, expected)
        id_val = self.tokenizer.val
        self._consume()
        return id_val

    def _consume_str(self, expected):
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
            raise self._err(f"{expected}, not '{Token.to_string(self.curt)}'")

    def _is_end_of_stmt(self, last_line):
        """Check if current token ends a statement."""
        if self.curt == Token.EOF:
            return True
        if self.curt == Token.SEMICOLON:
            return True
        return last_line < self.tokenizer.line

    def _end_of_stmt(self, last_line):
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
        raise self._err(f"Expected end of statement; not '{Token.to_string(self.curt)}'")

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

    def r_char(self):
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
        """Resolve a type name against this pod.

        Only returns the type if it actually exists (module can be imported).
        This prevents creating phantom types that don't really exist.
        """
        # Check if module can be imported before creating the type
        # This prevents returning types like testSys::DT that don't exist
        pod_name = self.pod.name()
        try:
            __import__(f'fan.{pod_name}.{name}', fromlist=[name])
        except ImportError:
            return None
        return self.pod.type(name, False)


class _UsingType:
    """Using import for specific type with optional alias."""

    def __init__(self, type_, name):
        self.type = type_
        self.name = name

    def resolve(self, name):
        return self.type if self.name == name else None
