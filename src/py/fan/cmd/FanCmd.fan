//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   5 Feb 2026  Creation
//

using util

**
** Fan command - runs Fantom main programs in Python
**
** This is the key command that allows running any Fantom Main class
** in the Python runtime, equivalent to how 'fan' runs them in the JVM.
**
** Usage:
**   py fan hx init ./myproject   Calls fan.hx.Main.main(["init", "./myproject"])
**   py fan hx run ./myproject    Calls fan.hx.Main.main(["run", "./myproject"])
**   py fan xeto help             Calls fan.xetom.Main.main(["help"])
**   py fan axonsh                Calls fan.axonsh.Main.main([])
**
** The pod name is mapped to its Python module:
**   hx     -> fan.hx.Main (delegates to HxCli commands)
**   xeto   -> fan.xetom.Main (delegates to XetoCmd commands)
**   axonsh -> fan.axonsh.Main (interactive shell)
**
internal class FanCmd : PyCmd
{
  override Str name() { "fan" }

  override Str summary() { "Run Fantom main programs in Python" }

  @Arg { help = "Pod name and arguments" }
  Str[] args := [,]

  ** Map of CLI names to their actual pod names
  ** Some CLIs (like xeto) delegate to a different pod (xetom)
  private static const Str:Str podMap := [
    "xeto": "xetom",  // xeto::Main delegates to xetom::Main
  ]

  override Int run()
  {
    if (!checkForPython) return 1

    if (args.isEmpty)
    {
      printLine
      printLine("Usage: py fan <pod> [args...]")
      printLine
      printLine("Examples:")
      printLine("  py fan hx init ./myproject   Initialize Haxall project")
      printLine("  py fan hx run ./myproject    Run Haxall daemon")
      printLine("  py fan xeto help             Xeto CLI help")
      printLine("  py fan xeto env              Show Xeto environment")
      printLine("  py fan axonsh                Start Axon shell")
      printLine
      return 0
    }

    // First arg is the pod/command name
    podName := args.first
    mainArgs := args.size > 1 ? args[1..-1] : Str[,]

    // Map CLI name to actual pod name if needed
    actualPod := podMap[podName] ?: podName

    if (verbose)
    {
      printLine("Running: fan.${actualPod}.Main.main(${mainArgs})")
      printLine("  Python: ${findPython}")
      printLine("  PYTHONPATH: ${dir.osPath}")
    }

    // Build Python script to run the main program
    script := buildMainScript(actualPod, mainArgs)

    // Run Python with the script
    return runPython(["-c", script])
  }

  ** Build Python script that invokes a pod's Main class
  private Str buildMainScript(Str podName, Str[] mainArgs)
  {
    // Escape args for Python string literals
    argsStr := mainArgs.map |a| { "\"${escapeStr(a)}\"" }.join(", ")

    return
      """import sys
         sys.path.insert(0, '.')

         try:
             from fan.${podName}.Main import Main
             from fan.sys.List import List
         except ImportError as e:
             print(f"ERROR: Cannot import fan.${podName}.Main: {e}")
             print(f"Make sure the pod '${podName}' has been transpiled to Python")
             sys.exit(1)

         # Convert Python list to Fantom List
         args = List.from_literal([${argsStr}], 'sys::Str')
         try:
             result = Main.main(args)
             sys.exit(result if result is not None else 0)
         except Exception as e:
             print(f"ERROR: {e}")
             import traceback
             traceback.print_exc()
             sys.exit(1)
         """
  }

  ** Escape special characters in a string for Python
  private Str escapeStr(Str s)
  {
    s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
  }
}
