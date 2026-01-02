//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//

using fanc
using util

**
** PyCmd is the command called by fanc (e.g., `fant -py testSys`)
**
class PyCmd : FancCmd
{
  override Str name() { "py" }

  override Str summary() { "Run tests using Python runtime" }

  @Arg { help = "Test target(s): pod, pod::Type, or pod::Type.method" }
  Str[]? targets

  override Int run()
  {
    // Forward to fanPy test command with targets
    if (targets == null || targets.isEmpty)
    {
      printLine("ERROR: No test targets specified")
      printLine("Usage: fant -py <pod>, <pod>::<Type>, or <pod>::<Type>.<method>")
      return 1
    }
    args := Str["test"]
    args.addAll(targets)
    return fanPy::Main.main(args)
  }
}
