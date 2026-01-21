#
# Unit - Unit of measurement for Fantom
#
import os
import re
from fan.sys.Obj import Obj

class Unit(Obj):
    """
    Unit represents a unit of measurement.
    """

    # Unit database - populated on first access
    _units_by_id = {}      # id -> Unit (all names/symbols)
    _units_list = []       # all unique units
    _quantities = {}       # quantity name -> [Unit, ...]
    _quantity_names = []   # ordered quantity names
    _initialized = False

    # Dimension names in order
    _DIM_NAMES = ['kg', 'm', 'sec', 'K', 'A', 'mol', 'cd']

    def __init__(self, name_or_ids, scale=1.0, offset=0.0, dim=None, definition=None, quantity=None):
        """
        Private constructor - use Unit(name) or Unit.from_str() for lookup.
        """
        # Handle lookup by name string
        if isinstance(name_or_ids, str):
            Unit._ensure_initialized()
            u = Unit._units_by_id.get(name_or_ids)
            if u is not None:
                # Return existing unit via __new__ pattern
                self.__dict__.update(u.__dict__)
                return
            # Not found - check if this is a new unit request
            raise Exception(f"Unknown unit: {name_or_ids}")

        # Internal construction with full parameters
        self._ids = name_or_ids if isinstance(name_or_ids, list) else [name_or_ids]
        self._scale = float(scale)
        self._offset = float(offset)
        self._dim = dim if dim else [0, 0, 0, 0, 0, 0, 0]  # kg, m, sec, K, A, mol, cd
        self._definition = definition or ""
        self._quantity = quantity or ""

    def __new__(cls, name_or_ids, scale=1.0, offset=0.0, dim=None, definition=None, quantity=None):
        """Handle Unit(name) as lookup, return cached instance."""
        if isinstance(name_or_ids, str):
            cls._ensure_initialized()
            u = cls._units_by_id.get(name_or_ids)
            if u is not None:
                return u
            raise Exception(f"Unknown unit: {name_or_ids}")
        # Internal construction
        return super().__new__(cls)

    @classmethod
    def _ensure_initialized(cls):
        """Load unit database from units.txt if not already loaded."""
        if cls._initialized:
            return
        cls._initialized = True
        cls._load_database()

    @classmethod
    def _load_database(cls):
        """Parse and load the units.txt database."""
        # Find units.txt relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Try several paths - Unit.py can be in different locations:
        # 1. fan/src/sys/py/fan/Unit.py -> fan/etc/sys/units.txt (../../../../etc)
        # 2. gen/py/fan/sys/Unit.py -> fan/etc/sys/units.txt (../../../../fan/etc)
        possible_paths = [
            # From fan/src/sys/py/fan/
            os.path.join(current_dir, '..', '..', '..', '..', 'etc', 'sys', 'units.txt'),
            # From gen/py/fan/sys/ (4 levels up to project root)
            os.path.join(current_dir, '..', '..', '..', '..', 'fan', 'etc', 'sys', 'units.txt'),
            # From gen/py/fan/ (3 levels up to project root)
            os.path.join(current_dir, '..', '..', '..', 'fan', 'etc', 'sys', 'units.txt'),
        ]

        units_path = None
        for path in possible_paths:
            path = os.path.normpath(path)
            if os.path.exists(path):
                units_path = path
                break

        if units_path is None:
            # Fallback to first path for error message
            units_path = os.path.normpath(possible_paths[0])

        current_quantity = "dimensionless"
        current_dim = None

        try:
            with open(units_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('//'):
                        continue

                    # Check for quantity header: -- name (dim)
                    if line.startswith('--'):
                        match = re.match(r'--\s*(\S+)\s*\(([^)]*)\)', line)
                        if match:
                            current_quantity = match.group(1)
                            dim_str = match.group(2)
                            if dim_str == 'null':
                                current_dim = None
                            else:
                                current_dim = cls._parse_dim_string(dim_str)
                            if current_quantity not in cls._quantities:
                                cls._quantities[current_quantity] = []
                                cls._quantity_names.append(current_quantity)
                        continue

                    # Parse unit definition
                    unit = cls._parse_unit_line(line, current_quantity, current_dim)
                    if unit:
                        cls._units_list.append(unit)
                        for id_ in unit._ids:
                            cls._units_by_id[id_] = unit
                        if current_quantity in cls._quantities:
                            cls._quantities[current_quantity].append(unit)

        except FileNotFoundError:
            # Create minimal fallback units
            cls._create_fallback_units()

    @classmethod
    def _parse_dim_string(cls, dim_str):
        """Parse dimension string like 'kg1*m-2*sec3' into exponent list."""
        dim = [0, 0, 0, 0, 0, 0, 0]
        if not dim_str or dim_str == 'null':
            return dim

        # Split by * and parse each component
        parts = dim_str.replace(' ', '').split('*')
        for part in parts:
            if not part:
                continue
            # Match dimension name and exponent
            match = re.match(r'([a-zA-Z]+)(-?\d+)?', part)
            if match:
                name = match.group(1)
                exp = int(match.group(2)) if match.group(2) else 1
                try:
                    idx = cls._DIM_NAMES.index(name)
                    dim[idx] = exp
                except ValueError:
                    pass  # Unknown dimension
        return dim

    @classmethod
    def _parse_unit_line(cls, line, quantity, default_dim):
        """Parse a unit definition line."""
        # Format: names; dimension; scale; offset
        # or:    names; ; scale; offset  (dimensionless)
        # or:    names  (dimensionless, scale=1, offset=0)

        parts = [p.strip() for p in line.split(';')]

        # Parse ids (comma-separated names)
        ids_str = parts[0]
        ids = [id_.strip() for id_ in ids_str.split(',') if id_.strip()]
        if not ids:
            return None

        # Parse dimension
        dim = default_dim[:] if default_dim else [0, 0, 0, 0, 0, 0, 0]
        if len(parts) > 1 and parts[1]:
            dim = cls._parse_dim_string(parts[1])

        # Parse scale
        scale = 1.0
        if len(parts) > 2 and parts[2]:
            try:
                scale = float(parts[2])
            except ValueError:
                pass

        # Parse offset
        offset = 0.0
        if len(parts) > 3 and parts[3]:
            try:
                offset = float(parts[3])
            except ValueError:
                pass

        # Create unit instance directly (bypass __new__ lookup)
        unit = object.__new__(Unit)
        unit._ids = ids
        unit._scale = scale
        unit._offset = offset
        unit._dim = dim
        unit._definition = line
        unit._quantity = quantity

        return unit

    @classmethod
    def _create_fallback_units(cls):
        """Create minimal fallback units if units.txt not found."""
        fallbacks = [
            (['meter', 'm'], 1.0, 0.0, [0, 1, 0, 0, 0, 0, 0], 'length'),
            (['kilometer', 'km'], 1000.0, 0.0, [0, 1, 0, 0, 0, 0, 0], 'length'),
            (['second', 's', 'sec'], 1.0, 0.0, [0, 0, 1, 0, 0, 0, 0], 'time'),
            (['minute', 'min'], 60.0, 0.0, [0, 0, 1, 0, 0, 0, 0], 'time'),
            (['hour', 'h', 'hr'], 3600.0, 0.0, [0, 0, 1, 0, 0, 0, 0], 'time'),
            (['kilogram', 'kg'], 1.0, 0.0, [1, 0, 0, 0, 0, 0, 0], 'mass'),
        ]
        for ids, scale, offset, dim, qty in fallbacks:
            unit = object.__new__(Unit)
            unit._ids = ids
            unit._scale = scale
            unit._offset = offset
            unit._dim = dim
            unit._definition = ""
            unit._quantity = qty
            cls._units_list.append(unit)
            for id_ in ids:
                cls._units_by_id[id_] = unit
            if qty not in cls._quantities:
                cls._quantities[qty] = []
                cls._quantity_names.append(qty)
            cls._quantities[qty].append(unit)

    # ---- Static Methods ----

    @staticmethod
    def from_str(name, checked=True):
        """Parse a Unit from string."""
        Unit._ensure_initialized()
        u = Unit._units_by_id.get(name)
        if u is not None:
            return u
        if checked:
            raise Exception(f"Unknown unit: {name}")
        return None

    @staticmethod
    def find(name, checked=True):
        """Find unit by name (alias for fromStr)."""
        return Unit.from_str(name, checked)

    @staticmethod
    def list_():
        """List all defined units."""
        from fan.sys.List import List
        from fan.sys.Type import Type
        Unit._ensure_initialized()
        result = List.from_list(Unit._units_list[:])
        result._listType = Type.find("sys::Unit[]")
        result._of = Type.find("sys::Unit")
        return result.to_immutable()

    @staticmethod
    def quantities():
        """List all quantity type names."""
        from fan.sys.List import List
        from fan.sys.Type import Type
        Unit._ensure_initialized()
        result = List.from_list(Unit._quantity_names[:])
        result._listType = Type.find("sys::Str[]")
        result._of = Type.find("sys::Str")
        return result.to_immutable()

    @staticmethod
    def quantity(name):
        """Get units for a quantity type."""
        from fan.sys.List import List
        from fan.sys.Type import Type
        Unit._ensure_initialized()
        units = Unit._quantities.get(name, [])
        result = List.from_list(units[:])
        result._listType = Type.find("sys::Unit[]")
        result._of = Type.find("sys::Unit")
        return result.to_immutable()

    @staticmethod
    def define(s):
        """Define a new unit from string specification."""
        from fan.sys.Err import ParseErr
        Unit._ensure_initialized()

        # Parse the definition string
        parts = [p.strip() for p in s.split(';')]

        # Parse ids - don't filter, check for empty ids explicitly
        ids_str = parts[0]
        ids_raw = [id_.strip() for id_ in ids_str.split(',')]

        # Check for empty ids (including empty first part or trailing commas)
        if not ids_raw or all(not id_ for id_ in ids_raw):
            raise ParseErr.make(f"Unit: {s}: No unit ids defined")

        # Check each id for validity
        ids = []
        for id_ in ids_raw:
            if not id_:
                raise ParseErr.make(f"Unit: {s}: Invalid unit id length 0")
            # Validate each character - only allow: alpha, _, %, $, /, or code > 127
            for ch in id_:
                code = ord(ch)
                if ch.isalpha() or ch == '_' or ch == '%' or ch == '$' or ch == '/' or code > 127:
                    continue
                raise ParseErr.make(f"Unit: {s}: Invalid unit id {id_} (invalid char '{ch}')")
            ids.append(id_)

        if not ids:
            raise ParseErr.make(f"Unit: {s}: No unit ids defined")

        # Check if already defined
        first_id = ids[0]
        if first_id in Unit._units_by_id:
            existing = Unit._units_by_id[first_id]
            # Check if it's a redefinition (error unless identical)
            raise Exception(f"Unit already defined: {first_id}")

        # Parse dimension with validation
        dim = [0, 0, 0, 0, 0, 0, 0]
        if len(parts) > 1 and parts[1]:
            dim = Unit._parse_dim_string_checked(parts[1], s)

        # Parse scale
        scale = 1.0
        if len(parts) > 2 and parts[2]:
            try:
                scale = float(parts[2])
            except ValueError:
                raise ParseErr.make(f"Unit: {s}")

        # Parse offset
        offset = 0.0
        if len(parts) > 3 and parts[3]:
            try:
                offset = float(parts[3])
            except ValueError:
                raise ParseErr.make(f"Unit: {s}")

        # Create unit
        unit = object.__new__(Unit)
        unit._ids = ids
        unit._scale = scale
        unit._offset = offset
        unit._dim = dim
        unit._definition = s
        unit._quantity = ""

        # Register
        Unit._units_list.append(unit)
        for id_ in ids:
            Unit._units_by_id[id_] = unit

        return unit

    @classmethod
    def _parse_dim_string_checked(cls, dim_str, original_str):
        """Parse dimension string with validation, throwing ParseErr on bad ratios."""
        from fan.sys.Err import ParseErr
        dim = [0, 0, 0, 0, 0, 0, 0]
        if not dim_str or dim_str == 'null':
            return dim

        # Split by * and parse each component
        parts = dim_str.replace(' ', '').split('*')
        for part in parts:
            if not part:
                continue
            # Match dimension name and exponent
            match = re.match(r'^([a-zA-Z]+)(-?\d+)?$', part)
            if not match:
                raise ParseErr.make(f"Unit: {original_str}: Bad ratio '{part}'")

            name = match.group(1)
            exp_str = match.group(2)

            # Validate dimension name
            if name not in cls._DIM_NAMES:
                raise ParseErr.make(f"Unit: {original_str}: Bad ratio '{part}'")

            try:
                exp = int(exp_str) if exp_str else 1
            except ValueError:
                raise ParseErr.make(f"Unit: {original_str}: Bad ratio '{part}'")

            idx = cls._DIM_NAMES.index(name)
            dim[idx] = exp
        return dim

    # ---- Instance Methods ----

    def ids(self):
        """Get unit identifiers as immutable list."""
        from fan.sys.List import List
        return List.from_list(self._ids[:]).to_immutable()

    def name(self):
        """Primary name (first id)."""
        return self._ids[0] if self._ids else ""

    def symbol(self):
        """Unit symbol (last id)."""
        return self._ids[-1] if self._ids else ""

    def scale(self):
        """Scale factor relative to base unit."""
        return self._scale

    def offset(self):
        """Offset for conversions (e.g., Celsius to Kelvin)."""
        return self._offset

    def definition(self):
        """Return the definition string (dynamically constructed)."""
        # Build like Java: ids joined with ", "; dim; scale; offset
        s = ", ".join(self._ids)
        if not self._is_dimensionless(self._dim):
            s += "; " + self.dim()
            if self._scale != 1.0 or self._offset != 0.0:
                s += "; " + str(self._scale)
                if self._offset != 0.0:
                    s += "; " + str(self._offset)
        return s

    def dim(self):
        """Dimension string (e.g., 'm1' or 'kg2*m-3')."""
        parts = []
        for i, exp in enumerate(self._dim):
            if exp != 0:
                parts.append(f"{Unit._DIM_NAMES[i]}{exp}")
        return '*'.join(parts) if parts else ""

    # Dimension exponent accessors
    def kg(self):
        return self._dim[0]

    def m(self):
        return self._dim[1]

    def sec(self):
        return self._dim[2]

    def k(self):
        return self._dim[3]

    def a(self):
        return self._dim[4]

    def mol(self):
        return self._dim[5]

    def cd(self):
        return self._dim[6]

    def convert_to(self, val, to):
        """Convert value from this unit to another unit."""
        # Check compatible dimensions
        if self._dim != to._dim:
            raise Exception(f"Incompatible units: {self.name()} and {to.name()}")

        # Convert: this -> base -> target
        # base = (val * scale) + offset
        # target = (base - to.offset) / to.scale
        base = (val * self._scale) + self._offset
        return (base - to._offset) / to._scale

    def convert_from(self, val, from_):
        """Convert value from another unit to this one."""
        return from_.convert_to(val, self)

    def mult(self, other):
        """Multiply units - instance method for ObjUtil compatibility."""
        return self.__mul__(other)

    def div(self, other):
        """Divide units - instance method for ObjUtil compatibility."""
        return self.__truediv__(other)

    # Unicode superscripts for exponents
    _SUPERSCRIPTS = {2: '\xb2', 3: '\xb3'}

    # Cache for mult/div results
    _combos = {}

    # ---- Operators ----

    def __mul__(self, other):
        """Multiply units (e.g., m * m = m², ft * ft = ft², kW * h = kWh)."""
        if not isinstance(other, Unit):
            raise TypeError(f"Cannot multiply Unit by {type(other)}")

        # Check cache first
        key = (id(self), '*', id(other))
        if key in Unit._combos:
            return Unit._combos[key]

        result = Unit._find_mult(self, other)
        Unit._combos[key] = result
        return result

    def __truediv__(self, other):
        """Divide units (e.g., km / h = km/h)."""
        if not isinstance(other, Unit):
            raise TypeError(f"Cannot divide Unit by {type(other)}")

        # Check cache first
        key = (id(self), '/', id(other))
        if key in Unit._combos:
            return Unit._combos[key]

        result = Unit._find_div(self, other)
        Unit._combos[key] = result
        return result

    @classmethod
    def _find_mult(cls, a, b):
        """Find result of a * b following Java implementation logic."""
        # If either is dimensionless, fail
        if cls._is_dimensionless(a._dim) or cls._is_dimensionless(b._dim):
            raise Exception(f"Cannot compute dimensionless: {a} * {b}")

        # Compute dim and scale of a * b
        new_dim = [a._dim[i] + b._dim[i] for i in range(7)]
        scale = a._scale * b._scale

        # Find all matching units
        matches = cls._match(new_dim, scale)
        if len(matches) == 1:
            return matches[0]

        # For same-symbol multiplication (m * m = m², ft * ft = ft²)
        if a.symbol() == b.symbol():
            for exp, sup in cls._SUPERSCRIPTS.items():
                expected_sym = a.symbol() + sup
                for m in matches:
                    if m.symbol() == expected_sym:
                        return m

        # Try expected name pattern: a_b
        expected_name = a.name() + "_" + b.name()
        for m in matches:
            if m.name() == expected_name:
                return m

        # If we have any matches, return first
        if matches:
            return matches[0]

        raise Exception(f"Cannot match to db: {a} * {b}")

    @classmethod
    def _find_div(cls, a, b):
        """Find result of a / b following Java implementation logic."""
        # If either is dimensionless, fail
        if cls._is_dimensionless(a._dim) or cls._is_dimensionless(b._dim):
            raise Exception(f"Cannot compute dimensionless: {a} / {b}")

        # Compute dim and scale of a / b
        new_dim = [a._dim[i] - b._dim[i] for i in range(7)]
        scale = a._scale / b._scale if b._scale != 0 else a._scale

        # Find all matching units
        matches = cls._match(new_dim, scale)
        if len(matches) == 1:
            return matches[0]

        # Try expected name pattern: a_per_b
        expected_name = a.name() + "_per_" + b.name()
        for m in matches:
            if expected_name in m.name():
                return m

        # If we have any matches, return first
        if matches:
            return matches[0]

        raise Exception(f"Cannot match to db: {a} / {b}")

    @classmethod
    def _match(cls, dim, scale):
        """Find all units matching dimension and scale (with loose approximation)."""
        cls._ensure_initialized()
        matches = []
        for unit in cls._units_list:
            if unit._dim == dim and cls._approx(unit._scale, scale):
                matches.append(unit)
        return matches

    @staticmethod
    def _approx(a, b):
        """Loose approximation for scale matching (from Java implementation)."""
        if a == b:
            return True
        # Pretty loose because database doesn't have super great resolution
        t = min(abs(a / 1e3), abs(b / 1e3))
        return abs(a - b) <= t

    @staticmethod
    def _is_dimensionless(dim):
        """Check if dimension is all zeros."""
        return all(d == 0 for d in dim)

    @classmethod
    def _find_by_dim(cls, dim, target_scale=None):
        """Find a unit by its dimension (fallback method)."""
        cls._ensure_initialized()
        for unit in cls._units_list:
            if unit._dim == dim:
                if target_scale is None or cls._approx(unit._scale, target_scale):
                    return unit
        return None

    # ---- Identity ----

    def to_str(self):
        """String representation (symbol)."""
        return self.symbol()

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return f"Unit({self.name()})"

    def equals(self, other):
        """Test equality."""
        if other is self:
            return True
        if not isinstance(other, Unit):
            return False
        return self._ids == other._ids

    def __eq__(self, other):
        return self.equals(other)

    def __hash__(self):
        return self.hash_()

    def hash_(self):
        """Hash code based on symbol."""
        return hash(self.symbol())

    def trap(self, name, args=None):
        """Dynamic slot access for dimension exponents."""
        if name in Unit._DIM_NAMES:
            idx = Unit._DIM_NAMES.index(name)
            return self._dim[idx]
        return super().trap(name, args)

    def typeof(self):
        from fan.sys.Type import Type
        return Type.find("sys::Unit")

    def literal_encode(self, encoder):
        """Encode for serialization.

        Simple types serialize as: Type("toStr")
        Example: sys::Unit("meter")
        """
        encoder.w_type(self.typeof())
        encoder.w('(')
        encoder.w_str_literal(self.to_str(), '"')
        encoder.w(')')
