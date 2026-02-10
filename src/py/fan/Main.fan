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
** Command line main for py
**
** Usage:
**   py help                     - Show available commands
**   py init                     - Initialize Python environment
**   py test <target>            - Run tests in Python
**   py fan <pod> <args>         - Run Fantom main program in Python
**
class Main
{
  static Int main(Str[] args)
  {
    // lookup command
    if (args.isEmpty) args = ["help"]
    name := args.first
    cmd := PyCmd.find(name)
    if (cmd == null)
    {
      echo("ERROR: unknown py command '$name'")
      return 1
    }

    // strip commandname from args and process as util::AbstractMain
    return cmd.main(args.dup[1..-1])
  }
}
