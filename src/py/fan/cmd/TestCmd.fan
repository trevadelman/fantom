//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//   5 Feb 2026  Renamed from fanPy to py
//

using util
using compiler

**
** Test command - runs Fantom tests in Python
**
** Usage:
**   py test testSys::BoolTest           Run single test class
**   py test testSys::BoolTest.testDefVal Run single method
**   py test testSys testHaystack        Run multiple pods
**
internal class TestCmd : PyCmd
{
  override Str name() { "test" }

  override Str summary() { "Run Fantom tests in Python" }

  @Arg { help = "Test targets (pod, type, or method)" }
  Str[] targets := [,]

  override Int run()
  {
    if (!checkForPython) return 1

    if (targets.isEmpty)
    {
      return err("No test targets specified. Usage: py test <target>...")
    }

    // Use util::TestRunner to run tests
    printLine
    printLine("Running Python tests...")
    printLine("  Python: ${findPython}")
    printLine("  PYTHONPATH: ${dir.osPath}")
    printLine

    // Build Python script to run tests
    script := buildTestScript(targets)

    // Run Python with the test script
    return runPython(["-c", script])
  }

  ** Build Python script that invokes util::TestRunner
  private Str buildTestScript(Str[] targets)
  {
    targetsStr := targets.join("\", \"")
    return
      """import sys
         sys.path.insert(0, '.')

         from fan.util.TestRunner import TestRunner
         from fan.sys.List import List

         targets = List.from_literal(["${targetsStr}"], 'sys::Str')
         result = TestRunner.make().main(targets)
         sys.exit(result if result is not None else 0)
         """
  }
}
