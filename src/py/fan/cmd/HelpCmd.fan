//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//   5 Feb 2026  Renamed from fanPy to py
//

using util

**
** Help command - lists available py commands
**
internal class HelpCmd : PyCmd
{
  override Str name() { "help" }

  override Str[] aliases() { ["-h", "-?"] }

  override Str summary() { "Print listing of available commands" }

  @Arg { help = "Command name for detailed help" }
  Str[] commandName := [,]

  override Int run()
  {
    // if we have a command name, print its usage
    if (commandName.size > 0)
    {
      cmdName := commandName[0]
      cmd := find(cmdName)
      if (cmd == null) return err("Unknown help command '$cmdName'")
      printLine
      ret := cmd.usage
      printLine
      return ret
    }

    // show summary for all commands
    cmds := list
    maxName := 4
    cmds.each |cmd| { maxName = maxName.max(cmd.name.size) }

    printLine
    printLine("py commands:")
    printLine
    cmds.each |cmd|
    {
      printLine("  " + cmd.name.padr(maxName) + "  " + cmd.summary)
    }
    printLine
    printLine("Use 'py help <command>' for more details")
    printLine
    printLine("Usage:")
    printLine("  py <command> [options]")
    printLine
    printLine("Examples:")
    printLine("  py help                     Show this help")
    printLine("  py init                     Initialize Python environment")
    printLine("  py test testSys::BoolTest   Run tests in Python")
    printLine("  py fan hx init ./myproject  Run hx init in Python")
    printLine("  py fan hx run ./myproject   Run hx run in Python")
    printLine
    return 0
  }
}
