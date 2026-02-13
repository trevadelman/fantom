#! /usr/bin/env fan
//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   2 Jan 2026  Creation
//   5 Feb 2026  Renamed from fanPy to py
//

using build

**
** Build: py
**
class Build : BuildPod
{
  new make()
  {
    podName = "py"
    summary = "Utilities for running Fantom in Python"
    meta    = ["org.name":     "Fantom",
               "org.uri":      "https://fantom.org/",
               "proj.name":    "Fantom Core",
               "proj.uri":     "https://fantom.org/",
               "license.name": "Academic Free License 3.0",
               "vcs.name":     "Git",
               "vcs.uri":      "https://github.com/fantom-lang/fantom",
               ]
    depends = ["sys 1.0",
               "build 1.0",
               "compiler 1.0",
               "util 1.0",
              ]
    srcDirs = [
               `fan/`,
               `fan/cmd/`,
              ]
    resDirs = [
               `res/`,
              ]
    docApi  = false
  }
}
