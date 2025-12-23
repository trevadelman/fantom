# Python Transpiler

Transpile Fantom source code to Python 3.

## Status

**Bootstrap/Proof-of-Concept** - Validates the architecture with minimal implementation.

## Usage

```bash
fanc py <podName>      # Transpile pod and dependencies to Python
fanc py -help          # Show options
```

Output is generated to `gen/py/fan/<podName>/`.

## Architecture

Follows the same pattern as the Java transpiler (`fan/java/`):

- **PythonCmd** - Extends TranspileCmd, orchestrates transpilation
- **PyPrinter** - Base class for code generation
- **PyTypePrinter** - Generates Python class definitions
- **PyExprPrinter** - Transpiles expressions
- **PyStmtPrinter** - Transpiles statements
- **PyUtil** - Utility functions

## Python Runtime

Native Python implementations for sys pod types are in `src/sys/py/fan/`:

- `Obj.py` - Base object class
- `Bool.py` - Boolean type (static methods on native bool)
- `Test.py` - Unit test base class
- `ObjUtil.py` - Runtime type operations
- `Err.py` - Error types

## Key Design Decisions

1. **Namespace prefix** - Output uses `fan/` prefix to avoid conflict with Python's built-in `sys` module
2. **Primitive types** - Bool, Int, Float use native Python types with static wrapper methods
3. **One file per type** - Each Fantom type becomes a Python file

## Current Limitations

- Only Bool type fully implemented
- Primitive method dispatch needs enhancement
- Missing many sys pod types

## Running Tests

```bash
# Transpile
fanc py testSys

# Copy runtime
cp src/sys/py/fan/*.py gen/py/fan/sys/

# Run test
cd gen/py
python3 -c "
import sys; sys.path.insert(0, '.')
from fan.sys.Test import Test
from fan.sys.ObjUtil import ObjUtil
exec(open('fan/testSys/BoolTest.py').read())
bt = BoolTest()
bt.testOperators()
print(f'Passed: {bt.verifyCount()} verifications')
"
```

## Bootstrap Strategy

This implementation follows a "tracer bullet" approach:

1. **Bootstrap (this PR)** - Build minimal end-to-end slice to validate architecture
   - Command infrastructure following Java transpiler patterns
   - Basic expression/statement/type printers
   - Minimal Python runtime (Obj, Bool, Test, ObjUtil, Err)
   - One passing test (BoolTest.testOperators) proves the pipeline

2. **Iterate** - Expand coverage incrementally
   - Add more expression types as tests demand
   - Expand Python runtime as needed
   - Each PR adds specific capability with tests

## Next Steps

**Phase 1: Core Types**
- [ ] Complete Bool (all methods, full test coverage)
- [ ] Int type and IntTest
- [ ] Str type and StrTest

**Phase 2: Collections**
- [ ] List type
- [ ] Map type
- [ ] Range type

**Phase 3: I/O & System**
- [ ] File/stream support
- [ ] Env access
- [ ] DateTime

**Phase 4: Advanced**
- [ ] Closures with bodies
- [ ] Actor concurrency
- [ ] Reflection/Type system
