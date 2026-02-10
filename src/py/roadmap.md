# py Pod - Migration Roadmap

This document tracks the migration from `fanPy` to `py` and the addition of new functionality.

## Overview

The `py` pod provides utilities for running Fantom programs in Python, following the same architecture as the `nodeJs` pod for JavaScript.

**Target Usage:**
```bash
py help                     # Show available commands
py init                     # Initialize Python environment
py test testSys::BoolTest   # Run tests in Python
py fan hx init ./myproject  # Run hx::Main with args ["init", "./myproject"]
py fan hx run ./myproject   # Run hx::Main with args ["run", "./myproject"]
py fan xeto help            # Run xetom::Main with args ["help"]
```

---

## Phase 1: Directory Structure and Core Files

### Status: COMPLETED

**1.1 Create directory structure**
- [x] `fan/src/py/` - Main pod directory
- [x] `fan/src/py/fan/` - Source files
- [x] `fan/src/py/fan/cmd/` - Command implementations
- [x] `fan/src/py/res/` - Resources

**1.2 Create core files (copy from fanPy, rename)**
- [x] `build.fan` - Build script (podName = "py")
- [x] `fan/Main.fan` - CLI entry point
- [x] `fan/PyCmd.fan` - Base command class (renamed from FanPyCmd)

**1.3 Create command files**
- [x] `fan/cmd/HelpCmd.fan` - Help command
- [x] `fan/cmd/TestCmd.fan` - Test runner command
- [x] `fan/cmd/InitCmd.fan` - NEW: Initialize Python venv
- [x] `fan/cmd/FanCmd.fan` - NEW: Run Fantom main programs

---

## Phase 2: New Functionality

### 2.1 InitCmd - Initialize Python Environment
**Status:** COMPLETED

Initialize a Python virtual environment with transpiled Fantom code:
```bash
py init                      # Default: lib/py/
py init -d /path/to/venv     # Custom directory
py init --uv                 # Use uv for fast venv creation
```

**Implementation:**
- [x] Check for Python 3.12+
- [x] Support uv for fast venv creation
- [x] Copy transpiled code from gen/py/
- [x] Create activation script

### 2.2 FanCmd - Run Fantom Main Programs
**Status:** COMPLETED

Run any Fantom pod's Main class in Python:
```bash
py fan hx init ./myproject   # Calls fan.hx.Main.main(["init", "./myproject"])
py fan hx run ./myproject    # Calls fan.hx.Main.main(["run", "./myproject"])
py fan xeto help             # Calls fan.xetom.Main.main(["help"])
py fan axonsh                # Calls fan.axonsh.Main.main([])
```

**Implementation:**
- [x] Parse pod name from first arg
- [x] Construct Python import path: `fan.{pod}.Main`
- [x] Call `Main.main(args)` with remaining args
- [x] Handle errors gracefully
- [x] Map CLI names to pods (xeto -> xetom)

### 2.3 Python Environment Management
**Status:** COMPLETED (in PyCmd.fan)

**Environment Variables:**
- `FAN_PYTHON` - Override Python executable path
- `FAN_PY_HOME` - Override transpiled code location (default: gen/py/)

**Python Discovery Order:**
1. `FAN_PYTHON` environment variable
2. `uv python find` (if uv installed)
3. `pyenv which python` (if pyenv installed)
4. `which python3` / `where python` (system)

**Version Check:**
- [x] Minimum: Python 3.12
- [x] Error with helpful message if version too low

---

## Phase 3: Shell Launcher

### 3.1 Create fan/bin/py
**Status:** COMPLETED

Shell script to launch py commands:
```bash
#!/bin/bash
. "${0%/*}/fanlaunch"
fanlaunch Fan py "$@"
```

### 3.2 Create fan/bin/pylaunch (optional)
**Status:** SKIPPED (not needed - fanlaunch handles it)

If Python-specific launch logic is needed (environment setup, etc.)

---

## Phase 4: Migration - Update References

### 4.1 Files in fan/src/py/ (internal)
**Status:** COMPLETED (created fresh, not copied from fanPy)

| File | Change | Status |
|------|--------|--------|
| `build.fan` | `podName = "py"` | DONE |
| `fan/Main.fan` | Error message: `"unknown py command"` | DONE |
| `fan/PyCmd.fan` | `appName() { "py ${name}" }`, `Log.get("py")` | DONE |
| `fan/cmd/HelpCmd.fan` | `"py commands:"`, `"py help <command>"` | DONE |

### 4.2 Files in python-fantom repo (external)
**Status:** COMPLETED

| File | Changes | Status |
|------|---------|--------|
| `build-test.sh` | `fanPy` -> `py` | DONE |
| `fanpy.sh` | DELETED (redundant wrapper) | DONE |
| `fanpy-test.sh` | DELETED (redundant wrapper) | DONE |
| `fanpy-build.sh` | DELETED (redundant wrapper) | DONE |
| `docs/development_guide.md` | Updated testing section | DONE |
| `readme.md` | Update fanPy references | DONE |
| `PR_SUMMARY.md` | Update references | OPTIONAL (PR docs) |
| `PR_ROADMAP.md` | Update references | OPTIONAL (PR docs) |

---

## Phase 5: Testing and Verification

### 5.1 Build and Test
- [ ] Build py pod: `fan src/py/build.fan`
- [ ] Test help: `fan py help`
- [ ] Test init: `fan py init`
- [ ] Test test runner: `fan py test testSys::BoolTest`
- [ ] Test fan cmd: `fan py fan hx help`

### 5.2 Integration Testing
- [ ] Verify `hx init` creates database
- [ ] Verify `hx run` starts server
- [ ] Verify `xeto help` shows commands
- [ ] Verify `axonsh` enters interactive mode

---

## Architecture Reference

### Comparison with nodeJs Pod

| nodeJs | py | Purpose |
|--------|-----|---------|
| `nodeJs init` | `py init` | Initialize runtime environment |
| `nodeJs run script.fan` | `py fan <pod> <args>` | Run Fantom code |
| `nodeJs test` | `py test` | Run tests |
| `nodeJs::Main` | `py::Main` | CLI entry point |
| `nodeJs::NodeJsCmd` | `py::PyCmd` | Base command class |

### File Structure (after migration)

```
fan/src/py/
  build.fan
  readme.md
  roadmap.md (this file)
  fan/
    Main.fan
    PyCmd.fan
    PyEnv.fan          # NEW: Python environment management
    cmd/
      HelpCmd.fan
      TestCmd.fan
      InitCmd.fan      # NEW: Initialize venv
      FanCmd.fan       # NEW: Run Fantom mains
  res/
    .gitkeep
```

---

## Timeline Estimate

| Phase | Effort | Status |
|-------|--------|--------|
| Phase 1: Structure | 30 min | COMPLETED |
| Phase 2: New Functionality | 2-3 hours | COMPLETED |
| Phase 3: Shell Launcher | 15 min | COMPLETED |
| Phase 4: Migration | 1 hour | COMPLETED |
| Phase 5: Testing | 1 hour | NOT STARTED |

**Remaining: ~1 hour (Phase 5 - Testing)**

---

## Notes

- The `fanPy` pod will be deprecated once `py` is fully functional
- Consider keeping `fanPy` as an alias during transition period
- The `py` name may conflict with Python aliases on some systems - document this
