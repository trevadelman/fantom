#! /usr/bin/env fan
//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   Jan 2025  Trevor Adelman  Creation
//

using build

**
** Build: concurrent Python natives
**
** This script packages Python native implementations into the concurrent.pod file.
**
class Build : BuildScript
{

//////////////////////////////////////////////////////////////////////////
// Compile
//////////////////////////////////////////////////////////////////////////

  @Target { help = "Compile Python natives for concurrent pod" }
  Void compile()
  {
    log.info("compile [py]")
    log.indent

    // Source and output directories
    pyDir := scriptFile.parent
    tempDir := scriptFile.parent + `temp-py/`

    // Clean and create temp directory
    tempDir.delete
    tempDir.create

    // Create output structure: py/fan/concurrent/
    outDir := tempDir.createDir("py").createDir("fan").createDir("concurrent")

    // Copy all Python files from current directory (not fan/ subdirectory)
    log.debug("Copying Python natives...")
    pyDir.listFiles.each |f|
    {
      if (f.ext == "py")
      {
        log.debug("  ${f.name}")
        f.copyTo(outDir + `${f.name}`)
      }
    }

    // Create __init__.py files for Python package structure
    log.debug("Creating __init__.py files...")
    createInitPy(tempDir + `py/`)
    createInitPy(tempDir + `py/fan/`)
    createInitPy(outDir)

    // Add Python files into pod file
    log.debug("Packaging into concurrent.pod...")
    jar := JdkTask.make(this).jarExe
    pod := devHomeDir + `lib/fan/concurrent.pod`
    Exec.make(this, [jar, "fu", pod.osPath, "-C", tempDir.osPath, "."], tempDir).run

    // Cleanup
    tempDir.delete

    log.unindent
    log.info("Python natives packaged into concurrent.pod")
  }

  private Void createInitPy(File dir)
  {
    initFile := dir + `__init__.py`
    initFile.out.print("# Auto-generated Python package marker\n").close
  }

//////////////////////////////////////////////////////////////////////////
// Clean
//////////////////////////////////////////////////////////////////////////

  @Target { help = "Delete all intermediate and target files" }
  Void clean()
  {
    log.info("clean [py]")
    Delete.make(this, scriptFile.parent + `temp-py/`).run
  }

//////////////////////////////////////////////////////////////////////////
// Full
//////////////////////////////////////////////////////////////////////////

  @Target { help = "Run clean, compile" }
  Void full()
  {
    clean
    compile
  }

}
