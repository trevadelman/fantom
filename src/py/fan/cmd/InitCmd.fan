//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   5 Feb 2026  Creation
//

using util

**
** Init command - initializes Python environment
**
** Creates a Python virtual environment with the transpiled Fantom code,
** similar to how nodeJs init sets up a Node.js environment.
**
** Usage:
**   py init                    Initialize in default location (lib/py/)
**   py init -d /path/to/venv   Initialize in custom directory
**   py init --uv               Use uv for faster venv creation
**
internal class InitCmd : PyCmd
{
  override Str name() { "init" }

  override Str summary() { "Initialize Python environment with transpiled code" }

  @Opt { help = "Target directory for Python environment"; aliases = ["d"] }
  override File dir := Env.cur.homeDir.plus(`lib/py/`)

  @Opt { help = "Use uv for venv creation (faster)" }
  Bool uv := false

  @Opt { help = "Force recreation even if exists" }
  Bool force := false

  override Int run()
  {
    if (!checkForPython) return 1

    printLine
    printLine("Initializing Python environment...")
    printLine("  Target: ${dir.osPath}")
    printLine("  Python: ${findPython}")
    printLine

    // Check if already exists
    venvDir := dir.plus(`venv/`)
    if (venvDir.exists && !force)
    {
      printLine("Python environment already exists at ${venvDir.osPath}")
      printLine("Use --force to recreate")
      return 0
    }

    // Create directory structure
    dir.create

    // Create virtual environment
    if (!createVenv(venvDir)) return 1

    // Copy transpiled code
    if (!copyTranspiledCode) return 1

    // Create activation helper
    createActivationHelper

    printLine
    printLine("Python environment initialized successfully!")
    printLine
    printLine("To activate:")
    printLine("  source ${venvDir.osPath}/bin/activate")
    printLine
    printLine("Or use py commands directly:")
    printLine("  py fan hx init ./myproject")
    printLine("  py test testSys::BoolTest")
    printLine

    return 0
  }

  ** Create Python virtual environment
  private Bool createVenv(File venvDir)
  {
    printLine("Creating virtual environment...")

    Str[] cmd := Str[,]
    if (uv && hasCmd("uv"))
    {
      cmd = ["uv", "venv", venvDir.osPath]
      printLine("  Using uv for fast venv creation")
    }
    else
    {
      cmd = [findPython, "-m", "venv", venvDir.osPath]
    }

    proc := Process(cmd)
    if (proc.run.join != 0)
    {
      return err("Failed to create virtual environment") == 0
    }

    printLine("  Created ${venvDir.osPath}")
    return true
  }

  ** Check if a command exists
  private Bool hasCmd(Str cmd)
  {
    which := "win32" == Env.cur.os ? "where" : "which"
    return Process([which, cmd]) { it.out = null }.run.join == 0
  }

  ** Copy transpiled code from gen/py/ to the environment
  private Bool copyTranspiledCode()
  {
    genDir := Env.cur.workDir.plus(`gen/py/`)
    if (!genDir.exists)
    {
      printLine("  Note: gen/py/ not found - run 'fanc py' first to transpile")
      return true  // Not an error, just informational
    }

    printLine("Copying transpiled code from ${genDir.osPath}...")

    // Copy fan/ and fanx/ directories
    ["fan", "fanx"].each |name|
    {
      srcDir := genDir.plus(`${name}/`)
      if (srcDir.exists)
      {
        dstDir := dir.plus(`${name}/`)
        srcDir.copyTo(dstDir, ["overwrite": true])
        printLine("  Copied ${name}/")
      }
    }

    return true
  }

  ** Create activation helper script
  private Void createActivationHelper()
  {
    // Create a simple helper script
    helper := dir.plus(`activate.sh`)
    out := helper.out
    out.printLine("#!/bin/bash")
    out.printLine("# Activate Python environment for Fantom")
    out.printLine("source \"${dir.osPath}/venv/bin/activate\"")
    out.printLine("export PYTHONPATH=\"${dir.osPath}:\$PYTHONPATH\"")
    out.close

    // Make executable on Unix
    if ("win32" != Env.cur.os)
    {
      Process(["chmod", "+x", helper.osPath]).run.join
    }
  }
}
