//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//   5 Feb 2026  Renamed from FanPyCmd to PyCmd
//

using util

**
** py command base class
**
** Provides common functionality for all py commands including:
** - Python discovery (FAN_PYTHON, uv, pyenv, system)
** - Version checking (Python 3.12+)
** - Directory management for gen/py output
**
abstract class PyCmd : AbstractMain
{
  ** Find a specific command or return null
  static PyCmd? find(Str name)
  {
    list.find |t| { t.name == name || t.aliases.contains(name) }
  }

  ** List installed commands
  static PyCmd[] list()
  {
    PyCmd[] acc := PyCmd#.pod.types.mapNotNull |t->PyCmd?|
    {
      if (t.isAbstract || !t.fits(PyCmd#)) return null
      return t.make
    }
    acc.sort |a, b| { a.name <=> b.name }
    return acc
  }

  ** App name is "py {name}"
  override final Str appName() { "py ${name}" }

  ** Log name is "py"
  override Log log() { Log.get("py") }

  ** Command name
  abstract Str name()

  ** Command aliases/shortcuts
  virtual Str[] aliases() { Str[,] }

  ** Run the command. Return zero on success
  abstract override Int run()

  ** Single line summary of the command for help
  abstract Str summary()

  @Opt { help="Verbose debug output"; aliases=["v"] }
  Bool verbose

  @Opt { help = "Root directory for Python gen output"; aliases = ["d"] }
  virtual File dir := Env.cur.workDir.plus(`gen/py/`)

//////////////////////////////////////////////////////////////////////////
// Python Environment
//////////////////////////////////////////////////////////////////////////

  ** Minimum required Python version
  static const Int minPythonMajor := 3
  static const Int minPythonMinor := 12

  ** Find the Python executable using discovery order:
  ** 1. FAN_PYTHON environment variable
  ** 2. uv python find (if uv installed)
  ** 3. pyenv which python (if pyenv installed)
  ** 4. which python3 / where python (system)
  protected Str findPython()
  {
    // 1. Check FAN_PYTHON environment variable
    fanPython := Env.cur.vars["FAN_PYTHON"]
    if (fanPython != null && !fanPython.isEmpty)
    {
      if (verbose) printLine("Using FAN_PYTHON: $fanPython")
      return fanPython
    }

    // 2. Try uv python find
    if (hasCmd("uv"))
    {
      buf := Buf()
      proc := Process(["uv", "python", "find"]) { it.out = buf.out }
      if (proc.run.join == 0)
      {
        python := buf.flip.readAllStr.trim
        if (!python.isEmpty)
        {
          if (verbose) printLine("Using uv python: $python")
          return python
        }
      }
    }

    // 3. Try pyenv which python
    if (hasCmd("pyenv"))
    {
      buf := Buf()
      proc := Process(["pyenv", "which", "python"]) { it.out = buf.out }
      if (proc.run.join == 0)
      {
        python := buf.flip.readAllStr.trim
        if (!python.isEmpty)
        {
          if (verbose) printLine("Using pyenv python: $python")
          return python
        }
      }
    }

    // 4. Fallback to system python3
    python := "win32" == Env.cur.os ? "python" : "python3"
    if (verbose) printLine("Using system python: $python")
    return python
  }

  ** Check if a command exists in PATH
  private Bool hasCmd(Str cmd)
  {
    which := "win32" == Env.cur.os ? "where" : "which"
    return Process([which, cmd]) { it.out = null }.run.join == 0
  }

  ** Check that Python exists and meets version requirements
  protected Bool checkForPython()
  {
    python := findPython

    // Check if python exists
    which := "win32" == Env.cur.os ? "where" : "which"
    if (Process([which, python]) { it.out = null }.run.join != 0)
    {
      err("Python not found: $python")
      printLine("Please ensure Python 3.12+ is installed and available in your PATH")
      printLine("Or set FAN_PYTHON environment variable to Python executable path")
      return false
    }

    // Check version is 3.12+
    buf := Buf()
    versionCmd := [python, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"]
    proc := Process(versionCmd) { it.out = buf.out }
    if (proc.run.join != 0)
    {
      err("Could not determine Python version")
      return false
    }

    version := buf.flip.readAllStr.trim
    dotIdx := version.index(".")
    if (dotIdx == null)
    {
      err("Could not parse Python version: $version")
      return false
    }

    major := Int.fromStr(version[0..<dotIdx], 10, false) ?: 0
    minorStr := version[dotIdx+1..-1]
    // Handle "3.12.1" -> take just "12"
    dotIdx2 := minorStr.index(".")
    if (dotIdx2 != null) minorStr = minorStr[0..<dotIdx2]
    minor := Int.fromStr(minorStr, 10, false) ?: 0

    if (major < minPythonMajor || (major == minPythonMajor && minor < minPythonMinor))
    {
      err("Python ${minPythonMajor}.${minPythonMinor}+ required, found $version")
      printLine("Please upgrade Python or set FAN_PYTHON to a newer version")
      printLine("Tip: Use 'uv python install 3.12' to install Python 3.12")
      return false
    }

    if (verbose) printLine("Python version: $version")
    return true
  }

  ** Get the Python executable path
  protected Str python() { findPython }

  ** Run a Python command with the transpiled code in PYTHONPATH
  protected Int runPython(Str[] args)
  {
    python := findPython

    cmd := [python]
    cmd.addAll(args)

    proc := Process(cmd)

    // Set PYTHONPATH and inherit existing environment
    proc.env["PYTHONPATH"] = dir.osPath
    Env.cur.vars.each |v, k| { proc.env[k] = v }

    return proc.run.join
  }

//////////////////////////////////////////////////////////////////////////
// Console
//////////////////////////////////////////////////////////////////////////

  ** Print a line to stdout
  Void printLine(Str line := "") { Env.cur.out.printLine(line) }

  ** Print error message and return 1
  Int err(Str msg) { printLine("ERROR: ${msg}"); return 1 }
}
