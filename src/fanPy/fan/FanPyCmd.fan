//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//

using util

**
** FanPy command base class
**
abstract class FanPyCmd : AbstractMain
{
  ** Find a specific command or return null
  static FanPyCmd? find(Str name)
  {
    list.find |t| { t.name == name || t.aliases.contains(name) }
  }

  ** List installed commands
  static FanPyCmd[] list()
  {
    FanPyCmd[] acc := FanPyCmd#.pod.types.mapNotNull |t->FanPyCmd?|
    {
      if (t.isAbstract || !t.fits(FanPyCmd#)) return null
      return t.make
    }
    acc.sort |a, b| { a.name <=> b.name }
    return acc
  }

  ** App name is "fanPy {name}"
  override final Str appName() { "fanPy ${name}" }

  ** Log name is "fanPy"
  override Log log() { Log.get("fanPy") }

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
// Python
//////////////////////////////////////////////////////////////////////////

  protected Bool checkForPython()
  {
    cmd := ["which", "python3"]
    if ("win32" == Env.cur.os) cmd = ["where", "python"]
    if (Process(cmd) { it.out = null }.run.join != 0)
    {
      err("Python not found")
      printLine("Please ensure Python 3 is installed and available in your PATH")
      return false
    }
    return true
  }

//////////////////////////////////////////////////////////////////////////
// Console
//////////////////////////////////////////////////////////////////////////

  ** Print a line to stdout
  Void printLine(Str line := "") { Env.cur.out.printLine(line) }

  ** Print error message and return 1
  Int err(Str msg) { printLine("ERROR: ${msg}"); return 1 }
}
