//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//

using compiler
using util

**
** Run tests using Python runtime
**
class TestCmd : FanPyCmd
{
  override Str name() { "test" }

  override Str[] aliases() { ["t"] }

  override Str summary() { "Run tests using Python runtime" }

  @Arg { help = "Test target(s): pod, pod::Type, or pod::Type.method" }
  Str[]? targets

  override Int run()
  {
    if (targets == null || targets.isEmpty)
      return err("No test targets specified")

    if (!checkForPython) return 1

    // Generate test runner script
    script := generateScript
    scriptFile := dir.plus(`__fanpy_test__.py`)
    scriptFile.out.print(script).close

    if (verbose)
    {
      printLine("Generated test script: $scriptFile")
      printLine(script)
    }

    // Run Python with the test script
    cmd := ["python3", scriptFile.osPath]
    if ("win32" == Env.cur.os) cmd[0] = "python"
    proc := Process(cmd) { it.dir = this.dir }
    result := proc.run.join

    // Clean up
    if (!verbose) scriptFile.delete

    return result
  }

  private Str generateScript()
  {
    // Get Python source directory
    pyDir := dir.osPath

    // Build imports for test pods - extract pod name from targets like "pod::Type.method"
    pods := targets.map |t->Str|
    {
      idx := t.index("::")
      return idx == null ? t : t[0..<idx]
    }.unique

    imports := StrBuf()
    lb := "{"
    rb := "}"
    pods.each |pod|
    {
      imports.add("# Import ${pod} pod types and access class to trigger registration\n")
      imports.add("import os\n")
      imports.add("pod_dir = os.path.join(sys.path[0], 'fan', '${pod}')\n")
      imports.add("if os.path.isdir(pod_dir):\n")
      imports.add("    for filename in os.listdir(pod_dir):\n")
      imports.add("        if filename.endswith('.py') and not filename.startswith('_'):\n")
      imports.add("            class_name = filename[:-3]\n")
      imports.add("            try:\n")
      imports.add("                mod = __import__(f'fan.${pod}.${lb}class_name${rb}', fromlist=[class_name])\n")
      imports.add("                getattr(mod, class_name)  # Access class to trigger Type registration\n")
      imports.add("            except Exception as e:\n")
      imports.add("                pass  # Ignore import errors for non-test types\n")
      imports.add("\n")
    }

    // Build targets list
    targetList := targets.map |t| { "\"$t\"" }.join(", ")

    return
      """#!/usr/bin/env python3
         #
         # Auto-generated test runner script
         #

         import sys
         sys.path.insert(0, '$pyDir')

         $imports

         from fan.util.TestRunner import TestRunner
         from fan.sys.List import List

         targets = List.from_literal([$targetList], "sys::Str")
         result = TestRunner.main(targets)
         sys.exit(result)
         """
  }
}
