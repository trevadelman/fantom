# Fantom Python Transpiler

This document covers the Python transpiler (`fanc py`) and test framework (`fanPy`).

## Quick Start

```bash
# Transpile a pod to Python
fanc py testSys

# Run tests in Python
fan fanPy test testSys::BoolTest
```

## Components

### fanc py (Transpiler)

Located in `src/fanc/fan/py/`, the transpiler converts Fantom source to Python:

```bash
fanc py <pod>           # Transpile pod and its dependencies
fanc py -help           # Show options
```

Output is written to `gen/py/` by default.

**Files:**
- `PythonCmd.fan` - Entry point (extends TranspileCmd)
- `PyTypePrinter.fan` - Generates Python classes
- `PyStmtPrinter.fan` - Generates statements
- `PyExprPrinter.fan` - Generates expressions
- `PyPrinter.fan` - Base printer
- `PyUtil.fan` - Utilities

### fanPy (Test Runner)

This pod runs transpiled Fantom tests in Python, following the same pattern as `nodeJs`:

```bash
fan fanPy test <target>     # Run tests
fan fanPy help              # Show commands
```

**Commands:**
- `test` - Run tests using `util::TestRunner`
- `help` - Show available commands

## Architecture

| JavaScript | Python |
|------------|--------|
| `fanc js <pod>` | `fanc py <pod>` |
| `fan nodeJs test <target>` | `fan fanPy test <target>` |

## Runtime

Hand-written Python natives live in `py/` directories within each pod:
- `src/sys/py/` - Core runtime (~75 files)
- `src/concurrent/py/` - Actors and futures
- `src/util/py/` - Utilities

For runtime implementation details, see `src/sys/py/design.md`.
