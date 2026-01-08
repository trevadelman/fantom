#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

"""
ObjEncoder serializes an object to an output stream using Fantom's
human-readable serialization format.
"""

import math


class ObjEncoder:
    """Serializes objects to Fantom serialization format."""

    def __init__(self, out, options=None):
        """Create encoder that writes to OutStream.

        Args:
            out: OutStream to write to
            options: Optional Map with encoding options:
                - indent: Number of spaces for indentation (default 0)
                - skipDefaults: Skip fields with default values (default False)
                - skipErrors: Skip non-serializable objects instead of throwing (default False)
        """
        self.out = out
        self.level = 0
        self.indent = 0
        self.skip_defaults = False
        self.skip_errors = False
        self.cur_field_type = None

        if options is not None:
            self._init_options(options)

    @staticmethod
    def encode(obj):
        """Encode object to string.

        Args:
            obj: Object to serialize

        Returns:
            Serialized string representation
        """
        from fan.sys.StrBuf import StrBuf
        buf = StrBuf.make()
        out = buf.out()
        ObjEncoder(out, None).write_obj(obj)
        return buf.to_str()

    def write_obj(self, obj):
        """Write object to output stream.

        Args:
            obj: Object to serialize
        """
        # null
        if obj is None:
            self.w("null")
            return

        # Python primitives
        t = type(obj)

        if t is bool:
            self.w("true" if obj else "false")
            return

        if t is int:
            self.w(str(obj))
            return

        if t is str:
            self.w_str_literal(obj, '"')
            return

        if t is float:
            self._write_float(obj)
            return

        # Check for Fantom objects with literal_encode method
        if hasattr(obj, 'literal_encode'):
            obj.literal_encode(self)
            return

        # Check for Fantom Float wrapper (from Float.make)
        if hasattr(obj, 'fanType_') and obj.fanType_ == 'sys::Float':
            self._write_float(float(obj))
            return

        # Check for Fantom List
        from fan.sys.List import List
        if isinstance(obj, List):
            self.write_list(obj)
            return

        # Check for Fantom Map
        from fan.sys.Map import Map
        if isinstance(obj, Map):
            self.write_map(obj)
            return

        # Check for @Serializable facet
        if hasattr(obj, 'typeof'):
            obj_type = obj.typeof()
            if hasattr(obj_type, 'facet'):
                from fan.sys.Type import Type
                try:
                    ser_type = Type.find("sys::Serializable")
                    ser = obj_type.facet(ser_type, False)
                    if ser is not None:
                        # Check if simple serialization
                        # Get simple field - default is False if not set
                        is_simple = self._get_facet_bool(ser, 'simple', False)
                        if is_simple:
                            self._write_simple(obj_type, obj)
                        else:
                            self._write_complex(obj_type, obj, ser)
                        return
                except Exception:
                    pass

        # Not serializable
        if self.skip_errors:
            self.w("null /* Not serializable: ")
            if hasattr(obj, 'typeof'):
                self.w(obj.typeof().qname())
            else:
                self.w(type(obj).__name__)
            self.w(" */")
        else:
            from fan.sys.Err import IOErr
            type_name = obj.typeof().qname() if hasattr(obj, 'typeof') else type(obj).__name__
            raise IOErr.make(f"Not serializable: {type_name}")

    def _write_float(self, val):
        """Write float value with proper encoding."""
        if math.isnan(val):
            self.w('sys::Float("NaN")')
        elif math.isinf(val):
            if val > 0:
                self.w('sys::Float("INF")')
            else:
                self.w('sys::Float("-INF")')
        else:
            s = str(val)
            # Ensure there's a decimal point
            if '.' not in s and 'e' not in s and 'E' not in s:
                s += '.0'
            self.w(s)
            self.w("f")

    def _write_simple(self, obj_type, obj):
        """Write @Serializable{simple=true} type.

        Simple types serialize as: Type("toStrValue")
        """
        self.w_type(obj_type)
        self.w('(')
        # Get string value via to_str
        s = str(obj)
        if hasattr(obj, 'to_str'):
            s = obj.to_str()
        self.w_str_literal(s, '"')
        self.w(')')

    def _write_complex(self, obj_type, obj, ser):
        """Write complex @Serializable type with fields."""
        self.w_type(obj_type)

        first = True
        defObj = None

        if self.skip_defaults:
            # Try to create default instance for comparison
            try:
                defObj = obj_type.make()
            except Exception:
                pass

        # Get fields
        fields = obj_type.fields()
        field_count = fields.size() if callable(getattr(fields, 'size', None)) else len(fields)
        for i in range(field_count):
            f = fields.get(i) if callable(getattr(fields, 'get', None)) else fields[i]

            # Skip static, transient, and synthetic fields
            if f.is_static() or f.is_synthetic():
                continue

            # Check for @Transient facet
            if hasattr(f, 'has_facet'):
                from fan.sys.Type import Type
                try:
                    if f.has_facet(Type.find("sys::Transient")):
                        continue
                except Exception:
                    pass

            # Get field value
            val = f.get(obj)

            # Skip if matches default
            if defObj is not None:
                defVal = f.get(defObj)
                try:
                    from fan.sys.ObjUtil import ObjUtil
                    if ObjUtil.equals(val, defVal):
                        continue
                except Exception:
                    if val == defVal:
                        continue

            # Open braces on first field
            if first:
                self.w('\n')
                self.w_indent()
                self.w('{\n')
                self.level += 1
                first = False

            # Write field name and value
            self.w_indent()
            self.w(f.name())
            self.w('=')

            # Get field type, handle type_() method name
            ft = None
            if hasattr(f, 'type_'):
                ft = f.type_()
            elif hasattr(f, 'type'):
                ft = f.type() if callable(f.type) else f.type
            if ft is not None and hasattr(ft, 'to_non_nullable'):
                ft = ft.to_non_nullable()
            self.cur_field_type = ft
            self.write_obj(val)
            self.cur_field_type = None

            self.w('\n')

        # Handle @collection
        is_collection = self._get_facet_bool(ser, 'collection', False)
        if is_collection:
            first = self._write_collection_items(obj_type, obj, first)

        # Close braces if we opened them
        if not first:
            self.level -= 1
            self.w_indent()
            self.w('}')

    def _write_collection_items(self, obj_type, obj, first):
        """Write collection items for @Serializable{collection=true}."""
        # Look up each method
        m = obj_type.method("each", False)
        if m is None:
            from fan.sys.Err import IOErr
            raise IOErr.make(f"Missing {obj_type.qname()}.each")

        enc = self

        def write_item(item):
            nonlocal first
            if first:
                enc.w('\n')
                enc.w_indent()
                enc.w('{\n')
                enc.level += 1
                first = False
            enc.w_indent()
            enc.write_obj(item)
            enc.w(',\n')
            return None

        m.call_on(obj, [write_item])
        return first

    def write_list(self, lst):
        """Write Fantom List.

        Args:
            lst: List to write
        """
        # Get element type - use static method or attribute
        from fan.sys.List import List
        if hasattr(lst, '_elementType'):
            of = lst._elementType
        elif hasattr(lst, 'of') and callable(lst.of):
            of = lst.of()
        else:
            of = List.of(lst)

        # Decide single or multi-line format
        nl = self._is_multi_line(of)

        # Check if we can use inferred type
        inferred = False
        if self.cur_field_type is not None:
            from fan.sys.Type import Type
            if hasattr(self.cur_field_type, 'fits'):
                try:
                    if self.cur_field_type.fits(Type.find("sys::List")):
                        inferred = True
                except:
                    pass

        # Clear field type
        self.cur_field_type = None

        # Write type prefix if not inferred (like JS does)
        if not inferred and of is not None:
            self.w_type(of)

        # Handle empty list - size may be method or property
        size = lst.size() if callable(getattr(lst, 'size', None)) else len(lst)
        if size == 0:
            self.w("[,]")
            return

        # Write items
        if nl:
            self.w('\n')
            self.w_indent()
        self.w('[')
        self.level += 1

        for i in range(size):
            if i > 0:
                self.w(',')
            if nl:
                self.w('\n')
                self.w_indent()
            self.write_obj(lst.get(i))

        self.level -= 1
        if nl:
            self.w('\n')
            self.w_indent()
        self.w(']')

    def write_map(self, m):
        """Write Fantom Map.

        Args:
            m: Map to write
        """
        # Get map type
        t = m.typeof()

        # Decide single or multi-line format
        nl = False
        if hasattr(t, 'k') and hasattr(t, 'v'):
            nl = self._is_multi_line(t.k) or self._is_multi_line(t.v)

        # Check if we can use inferred type (like JS: curFieldType instanceof MapType)
        inferred = False
        if self.cur_field_type is not None:
            from fan.sys.Type import Type, MapType
            if isinstance(self.cur_field_type, MapType):
                inferred = True

        # Clear field type so it doesn't get used for inference again
        self.cur_field_type = None

        # If we don't have an inferred type, then prefix with type (matching JS pattern)
        if not inferred:
            self.w_type(t)

        # Handle empty map
        if m.is_empty():
            self.w("[:]")
            return

        # Write items
        self.level += 1
        self.w('[')
        first = True
        keys = m.keys()
        # Handle both Fantom List and Python list
        key_count = keys.size() if callable(getattr(keys, 'size', None)) else len(keys)

        # Get value type for inference (if MapType with v attribute)
        val_type = None
        if hasattr(t, 'v'):
            val_type = t.v
            if val_type is not None and hasattr(val_type, 'to_non_nullable'):
                val_type = val_type.to_non_nullable()

        for i in range(key_count):
            if first:
                first = False
            else:
                self.w(',')
            if nl:
                self.w('\n')
                self.w_indent()
            # Handle both Fantom List.get() and Python list indexing
            key = keys.get(i) if callable(getattr(keys, 'get', None)) else keys[i]
            val = m.get(key)
            self.write_obj(key)
            self.w(':')
            # Set curFieldType for value type inference
            self.cur_field_type = val_type
            self.write_obj(val)
            self.cur_field_type = None
        self.w(']')
        self.level -= 1

    def _is_multi_line(self, t):
        """Check if type should use multi-line format."""
        if t is None:
            return False
        if hasattr(t, 'pod'):
            from fan.sys.Pod import Pod
            try:
                return t.pod() != Pod.find("sys")
            except:
                return False
        return False

    def w_type(self, t):
        """Write type signature.

        Args:
            t: Type to write

        Returns:
            self for chaining
        """
        if t is not None:
            sig = t.signature() if hasattr(t, 'signature') else str(t)
            self.w(sig)
        return self

    def w_str_literal(self, s, quote):
        """Write escaped string literal.

        Args:
            s: String to write
            quote: Quote character (" or `)

        Returns:
            self for chaining
        """
        self.w(quote)
        for c in s:
            if c == '\n':
                self.w('\\n')
            elif c == '\r':
                self.w('\\r')
            elif c == '\f':
                self.w('\\f')
            elif c == '\t':
                self.w('\\t')
            elif c == '\\':
                self.w('\\\\')
            elif c == '"' and quote == '"':
                self.w('\\"')
            elif c == '`' and quote == '`':
                self.w('\\`')
            elif c == '$':
                self.w('\\$')
            else:
                self.w(c)
        self.w(quote)
        return self

    def w_indent(self):
        """Write indentation.

        Returns:
            self for chaining
        """
        num = self.level * self.indent
        for _ in range(num):
            self.w(' ')
        return self

    def w(self, s):
        """Write string to output.

        Args:
            s: String to write

        Returns:
            self for chaining
        """
        for c in str(s):
            self.out.write_char(ord(c))
        return self

    def _init_options(self, options):
        """Initialize from options map."""
        indent = options.get("indent")
        if indent is not None:
            self.indent = int(indent)

        skipDefaults = options.get("skipDefaults")
        if skipDefaults is not None:
            self.skip_defaults = bool(skipDefaults)

        skipErrors = options.get("skipErrors")
        if skipErrors is not None:
            self.skip_errors = bool(skipErrors)

    def _get_facet_bool(self, facet, name, default):
        """Get a boolean field from a facet, with default if not set.

        Args:
            facet: Facet instance (may be FacetInstance or actual facet class)
            name: Field name to get
            default: Default value if field not set

        Returns:
            Boolean value of field or default
        """
        # Try direct attribute access (_fieldName pattern)
        attr_name = f"_{name}"
        if hasattr(facet, attr_name):
            val = getattr(facet, attr_name)
            if val is not None:
                return bool(val)
        # Try calling it as a method (actual facet class pattern)
        if hasattr(facet, name):
            val = getattr(facet, name)
            if callable(val):
                try:
                    return bool(val())
                except:
                    pass
            else:
                return bool(val)
        # Try trap for dynamic access
        if hasattr(facet, 'trap'):
            try:
                val = facet.trap(name)
                if val is not None:
                    return bool(val)
            except:
                pass
        return default
