//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//

using util

**
** Help command
**
class HelpCmd : FanPyCmd
{
  override Str name() { "help" }

  override Str summary() { "Print listing of available commands" }

  @Arg { help="Name of command to get help on" }
  Str? commandName

  override Int run()
  {
    if (commandName == null)
    {
      printLine
      printLine("fanPy commands:")
      FanPyCmd.list.each |c|
      {
        printLine("  ${c.name.padr(12)} $c.summary")
      }
      printLine
      printLine("Use 'fanPy help <command>' for more details")
    }
    else
    {
      cmd := FanPyCmd.find(commandName)
      if (cmd == null) return err("Unknown command '$commandName'")
      printLine
      printLine("Usage:")
      printLine("  fanPy $cmd.name [options]")
      printLine
      cmd.usage
    }
    return 0
  }
}
