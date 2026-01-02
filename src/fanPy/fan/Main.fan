//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//

using util

**
** Command line main for fanPy
**
class Main
{
  static Int main(Str[] args)
  {
    // lookup command
    if (args.isEmpty) args = ["help"]
    name := args.first
    cmd := FanPyCmd.find(name)
    if (cmd == null)
    {
      echo("ERROR: unknown fanPy command '$name'")
      return 1
    }

    // strip commandname from args and process as util::AbstractMain
    return cmd.main(args.dup[1..-1])
  }
}
