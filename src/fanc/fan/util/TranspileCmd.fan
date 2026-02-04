//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   12 May 2025  Brian Frank  Creation
//

using build
using compiler
using util

**
** Base class for transpiler commands
**
abstract class TranspileCmd : FancCmd
{

  @Opt { help = "Output directory" }
  File outDir := Env.cur.workDir + `gen/$name/`

  @Arg { help = "Target pod(s)" }
  Str[] podNames := [,]

//////////////////////////////////////////////////////////////////////////
// Run
//////////////////////////////////////////////////////////////////////////

  ** Call compilePod on every target
  override final Int run()
  {
    init
    return transpile
  }

  ** Standard initializaton
  virtual Void init()
  {
    // flatten depends
    flattenPods
  }

  ** Delete outDir and run compilePod on all pods
  virtual Int transpile()
  {
    // always start fresh
    outDir.delete

    // generate code for every target pod
    pods.each |pod| { compilePod(pod) }
    return 0
  }

//////////////////////////////////////////////////////////////////////////
// Pods
//////////////////////////////////////////////////////////////////////////

  ** Expand command line pod names to their full dependency chain.
  ** We require all podNames to be pre-compiled using normal Fantom compilation
  Void flattenPods()
  {
    // resolve pod names to installed precompiled pods
    Pod[] pods := podNames.map |name->Pod| { Pod.find(name) }
    pods = Pod.flattenDepends(pods)
    pods = Pod.orderByDepends(pods)

    // map Pods to TranspilePod instances, skipping non-transpilable pods
    pods.each |pod|
    {
      tp := transpilePod(pod)
      if (tp != null) this.pods.add(tp)
    }
  }

  ** Load transpile pod, returns null if pod cannot be transpiled
  private TranspilePod? transpilePod(Pod pod)
  {
    buildScript := buildScriptMap[pod.name]
    if (buildScript == null)
    {
      log.warn("Skipping pod '$pod.name' (no fan/ source directory - resource-only or Java-native)")
      return null
    }

    return TranspilePod {
      it.name        = pod.name
      it.version     = pod.version
      it.podFile     = pod->loadFile
      it.buildScript = buildScript
    }
  }

  ** Map of pod name to build scripts for environment
  once Str:File buildScriptMap()
  {
    // we rely on the convention that all pods are in a directory
    // of their name and contain a fan/ source directory
    acc := Str:File[:]
    Env.cur.path.each |path|
    {
      path.plus(`src/`).walk |f|
      {
        if (f.name == "build.fan" && f.plus(`fan/`).exists)
        {
          podName := f.parent.name
          if (acc[podName] == null) acc[podName] = f
        }
      }
    }
    return acc.toImmutable
  }

//////////////////////////////////////////////////////////////////////////
// Compile
//////////////////////////////////////////////////////////////////////////

  ** Compile build script into AST
  virtual Void compilePod(TranspilePod pod)
  {
    // info
    info("\n## Transpile $this.name [$pod.name]")

    // run only the front end
    this.compiler = Compiler(stdCompilerInput(pod))
    compiler.frontend

    // transpile the pod
    genPod(compiler.pod)

    this.compiler = null
  }

  ** Use the build script to generate the standard compiler input and then
  ** inovke the callback on it for additonal configuration.
  virtual CompilerInput stdCompilerInput(TranspilePod pod, |CompilerInput|? f := null)
  {
    buildPod    := Env.cur.compileScript(pod.buildScript).pod
    buildType   := buildPod.types.find |t| { t.fits(BuildPod#) }
    buildScript := (BuildPod)buildType.make
    input       := buildScript.stdFanCompilerInput
    input.version = pod.version
    if (f != null) input.with(f)
    return input
  }

//////////////////////////////////////////////////////////////////////////
// Generation
//////////////////////////////////////////////////////////////////////////

  ** Generate pod which calls genType for each non-synthetic
  virtual Void genPod(PodDef pod)
  {
    pod.typeDefs.each |type|
    {
      genType(type)
    }
  }

  ** Generate non-synthetic type
  virtual Void genType(TypeDef type)
  {
    echo("genType $type")
  }

//////////////////////////////////////////////////////////////////////////
// Fields
//////////////////////////////////////////////////////////////////////////

  ** Pod data with flattened dependency chain
  TranspilePod[] pods := [,]

  ** Compiler for current pod
  Compiler? compiler

}

**************************************************************************
** TranspilePod
**************************************************************************

**
** Pod data for every pod to comile
**
class TranspilePod
{
  new make(|This| f) { f(this) }

  const Str name           // pod name
  const Version version    // version
  const File podFile       // precompiled "foo.pod" file
  const File buildScript   // "build.fan" file

  override Str toStr() { "$name [$podFile.osPath]" }
}

