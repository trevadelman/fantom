//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   Dec 2025  Creation
//

using compiler

**
** Python transpiler utilities
**
class PyUtil
{
  ** Get output file for a type
  ** Uses fan/{podName}/ namespace to avoid Python built-in conflicts
  static File typeFile(File outDir, TypeDef t)
  {
    outDir + `fan/${t.pod.name}/${t.name}.py`
  }

  ** Get output directory for a pod
  ** Uses fan/{podName}/ namespace to avoid Python built-in conflicts
  static File podDir(File outDir, Str podName)
  {
    outDir + `fan/${podName}/`
  }

  ** Convert pod name to Python import path
  ** e.g., "sys" -> "fan.sys", "testSys" -> "fan.testSys"
  static Str podImport(Str podName)
  {
    "fan.${podName}"
  }

  ** Python reserved words that need to be escaped
  static const Str:Str reservedWords
  static
  {
    m := Str:Str[:]
    // Python keywords
    [
      "False", "None", "True", "and", "as", "assert", "async", "await",
      "break", "class", "continue", "def", "del", "elif", "else", "except",
      "finally", "for", "from", "global", "if", "import", "in", "is",
      "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
      "while", "with", "yield",
      // Built-in functions that could conflict
      "type", "hash", "id", "list", "map", "str", "int", "float", "bool",
      "self"
    ].each |name| { m[name] = "${name}_" }
    reservedWords = m.toImmutable
  }

  ** Escape Python reserved words and invalid characters
  static Str escapeName(Str name)
  {
    // First replace $ with _ (Fantom synthetic names use $)
    escaped := name.replace("\$", "_")
    // Then check for reserved words
    return reservedWords.get(escaped, escaped)
  }

  ** Convert Fantom boolean literal to Python
  static Str boolLiteral(Bool val)
  {
    val ? "True" : "False"
  }

  ** Convert Fantom null literal to Python
  static Str nullLiteral()
  {
    "None"
  }

  ** Is this a native Python type (uses static method dispatch)
  static Bool isPyNative(CType t)
  {
    t.isObj || t.isStr || t.isVal
  }

  ** Map of method qname to unary operators
  static once Str:Str unaryOperators()
  {
    [
      "sys::Bool.not":     "not ",
      "sys::Int.negate":   "-",
      "sys::Float.negate": "-",
    ].toImmutable
  }

  ** Map of method qname to binary operators
  static once Str:Str binaryOperators()
  {
    [
      "sys::Str.plus":        "+",

      "sys::Int.plus":        "+",
      "sys::Int.minus":       "-",
      "sys::Int.mult":        "*",
      // Int.div intentionally NOT mapped - Python // has floor division semantics
      // but Fantom uses truncated division (toward zero)
      // Handled by ObjUtil.div() in PyExprPrinter.divOp()
      // Int.mod intentionally NOT mapped - Python % has different semantics
      // for negative numbers (floor division vs truncated division)
      // Handled by ObjUtil.mod() in PyExprPrinter.modOp()
      "sys::Int.plusFloat":   "+",
      "sys::Int.minusFloat":  "-",
      "sys::Int.multFloat":   "*",
      "sys::Int.divFloat":    "/",

      "sys::Float.plus":      "+",
      "sys::Float.minus":     "-",
      "sys::Float.mult":      "*",
      "sys::Float.div":       "/",
      "sys::Float.plusInt":   "+",
      "sys::Float.minusInt":  "-",
      "sys::Float.multInt":   "*",
      "sys::Float.divInt":    "/",
    ].toImmutable
  }

  ** The instance side method name for a constructor
  static Str ctorImplName(CMethod x)
  {
    "${x.name}_init_"
  }

  ** Handle special method names
  static Str methodName(CMethod x)
  {
    n := x.name
    if (n.startsWith("instance\$init\$")) return "instance_init_"
    return escapeName(n)
  }
}
