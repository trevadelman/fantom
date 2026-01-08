//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   Dec 2025  Creation
//

using compiler

**
** Python expression printer
**
class PyExprPrinter : PyPrinter
{
  new make(PyPrinter parent) : super.make(parent.m.out)
  {
    this.m = parent.m
  }

  ** Print an expression
  Void expr(Expr e)
  {
    switch (e.id)
    {
      case ExprId.nullLiteral:     nullLiteral
      case ExprId.trueLiteral:     trueLiteral
      case ExprId.falseLiteral:    falseLiteral
      case ExprId.intLiteral:      intLiteral(e)
      case ExprId.floatLiteral:    floatLiteral(e)
      case ExprId.strLiteral:      strLiteral(e)
      case ExprId.listLiteral:     listLiteral(e)
      case ExprId.mapLiteral:      mapLiteral(e)
      case ExprId.rangeLiteral:    rangeLiteral(e)
      case ExprId.durationLiteral: durationLiteral(e)
      case ExprId.decimalLiteral:  decimalLiteral(e)
      case ExprId.uriLiteral:      uriLiteral(e)
      case ExprId.localVar:        localVar(e)
      case ExprId.thisExpr:        thisExpr
      case ExprId.superExpr:       superExpr(e)
      case ExprId.call:            call(e)
      case ExprId.construction:    construction(e)
      case ExprId.field:           field(e)
      case ExprId.assign:          assign(e)
      case ExprId.same:            same(e)
      case ExprId.notSame:         notSame(e)
      case ExprId.boolNot:         boolNot(e)
      case ExprId.boolOr:          boolOr(e)
      case ExprId.boolAnd:         boolAnd(e)
      case ExprId.cmpNull:         cmpNull(e)
      case ExprId.cmpNotNull:      cmpNotNull(e)
      case ExprId.isExpr:          isExpr(e)
      case ExprId.isnotExpr:       isnotExpr(e)
      case ExprId.asExpr:          asExpr(e)
      case ExprId.coerce:          coerce(e)
      case ExprId.ternary:         ternary(e)
      case ExprId.elvis:           elvis(e)
      case ExprId.shortcut:        shortcut(e)
      case ExprId.closure:         closure(e)
      case ExprId.staticTarget:    staticTarget(e)
      case ExprId.typeLiteral:     typeLiteral(e)
      case ExprId.slotLiteral:     slotLiteral(e)
      case ExprId.itExpr:          itExpr(e)
      case ExprId.throwExpr:       throwExpr(e)
      default:
        w("None")  // Placeholder for unimplemented expr: ${e.id}
    }
  }

//////////////////////////////////////////////////////////////////////////
// Literals
//////////////////////////////////////////////////////////////////////////

  private Void nullLiteral() { none }

  private Void trueLiteral() { true_ }

  private Void falseLiteral() { false_ }

  private Void intLiteral(LiteralExpr e) { w(e.val) }

  private Void floatLiteral(LiteralExpr e) { w(e.val) }

  private Void strLiteral(LiteralExpr e) { str(e.val) }

  private Void listLiteral(ListLiteralExpr e)
  {
    // Generate type-aware list: List.from_literal([items], elementType)
    // Extract element type from ListType
    listType := e.ctype
    CType? elemType := null

    // Try to get the element type from the parameterized list type
    if (!listType.isGeneric)
    {
      try
      {
        elemType = listType->v  // ListType has v() method returning element type
      }
      catch (Err err)
      {
        // Fallback to Obj?
        elemType = listType.pod.resolveType("Obj", true)?.toNullable
      }
    }

    // Use Obj? as fallback if we couldn't determine type
    elemSig := elemType?.signature ?: "sys::Obj?"

    w("List.from_literal([")
    e.vals.each |val, i|
    {
      if (i > 0) w(", ")
      expr(val)
    }
    w("], ")
    str(elemSig)
    w(")")
  }

  private Void mapLiteral(MapLiteralExpr e)
  {
    // Generate type-aware map: Map.from_literal([keys], [vals], keyType, valType)
    // Extract key/value types (explicit or inferred from compiler)
    mapType := e.ctype

    // Get the MapType's K and V types
    // ctype should be a MapType with k and v methods
    CType? keyType := null
    CType? valType := null

    // Try to get key/value types via the k and v methods
    if (mapType.isGeneric)
    {
      // For generic maps, use Obj:Obj? as default
      keyType = mapType.pod.resolveType("Obj", false)
      valType = mapType.pod.resolveType("Obj", true)?.toNullable
    }
    else
    {
      // Try to access the parametrized types
      // MapType has k() and v() methods that return CType
      try
      {
        keyType = mapType->k
        valType = mapType->v
      }
      catch (Err err)
      {
        // Fallback to Obj:Obj?
        keyType = mapType.pod.resolveType("Obj", false)
        valType = mapType.pod.resolveType("Obj", true)?.toNullable
      }
    }

    // Use Obj:Obj? as fallback if we couldn't determine types
    keySig := keyType?.signature ?: "sys::Obj"
    valSig := valType?.signature ?: "sys::Obj?"

    w("Map.from_literal([")
    // Keys array
    e.keys.each |key, i|
    {
      if (i > 0) w(", ")
      expr(key)
    }
    w("], [")
    // Values array
    e.vals.each |val, i|
    {
      if (i > 0) w(", ")
      expr(val)
    }
    w("], ")
    // Key type
    str(keySig)
    w(", ")
    // Value type
    str(valSig)
    w(")")
  }

  private Void rangeLiteral(RangeLiteralExpr e)
  {
    // Generate Range.make(start, end, exclusive)
    w("Range.make(")
    expr(e.start)
    w(", ")
    expr(e.end)
    if (e.exclusive)
      w(", True")
    w(")")
  }

  private Void durationLiteral(LiteralExpr e)
  {
    // Duration literal - value is in nanoseconds
    dur := e.val as Duration
    if (dur != null)
    {
      w("Duration.make(").w(dur.ticks).w(")")
    }
    else
    {
      w("Duration.make(0)")
    }
  }

  private Void decimalLiteral(LiteralExpr e)
  {
    // Decimal literal (5d suffix) - emit as Decimal.make("value")
    // Matches JS transpiler pattern: sys.Decimal.make(value)
    // Use string constructor to preserve precision for large values
    val := e.val.toStr
    w("Decimal.make(\"").w(val).w("\")")
  }

  private Void uriLiteral(LiteralExpr e)
  {
    // URI literal `http://example.com` -> Uri.from_str("http://example.com")
    uri := e.val as Uri
    if (uri != null)
    {
      w("Uri.from_str(").str(uri.toStr).w(")")
    }
    else
    {
      w("Uri.from_str(").str(e.val.toStr).w(")")
    }
  }

//////////////////////////////////////////////////////////////////////////
// Variables
//////////////////////////////////////////////////////////////////////////

  private Void localVar(LocalVarExpr e)
  {
    varName := e.var.name

    // Check if we're in a closure and this variable has a wrapper
    // If so, use the wrapper name instead of the original variable name
    if (m.inWrappedClosure)
    {
      wrapperName := m.getWrapper(varName)
      if (wrapperName != null)
      {
        w(escapeName(wrapperName))
        return
      }
    }

    w(escapeName(varName))
  }

  private Void thisExpr() { w("self") }

  private Void superExpr(SuperExpr e) { w("super()") }

  private Void itExpr(Expr e)
  {
    // "it" is the implicit closure parameter - output as "it"
    w("it")
  }

  private Void throwExpr(Expr e)
  {
    // throw as an expression (used in elvis, ternary, etc.)
    // Python's `raise` is a statement, so we use a helper function
    // ObjUtil.throw_(err) raises the exception and never returns
    te := e as ThrowExpr
    w("ObjUtil.throw_(")
    expr(te.exception)
    w(")")
  }

//////////////////////////////////////////////////////////////////////////
// Calls
//////////////////////////////////////////////////////////////////////////

  private Void call(CallExpr e)
  {
    // Skip compiler-injected const field validation calls (checkInCtor, enterCtor, exitCtor, checkFields$*)
    // These are added by ConstChecks.fan for runtime validation of const field setting.
    // In Python we skip these since const protection is not strictly enforced.
    // They reference 'this' which doesn't exist in static context (e.g., static factory methods).
    methodName := e.method.name
    if (methodName == "checkInCtor" || methodName == "enterCtor" || methodName == "exitCtor" ||
        methodName.startsWith("checkFields\$"))
    {
      // Output None as a placeholder (these are always no-return statements)
      w("None")
      return
    }

    // Handle safe navigation operator (?.): short-circuit to null if target is null
    // Pattern: ((lambda _safe_: None if _safe_ is None else <call>)(<target>))
    if (e.isSafe && e.target != null)
    {
      w("((lambda _safe_: None if _safe_ is None else ")
      safeCallBody(e)
      w(")(")
      expr(e.target)
      w("))")
      return
    }

    // Check if this is a cvar wrapper call (closure-captured variable)
    // Pattern: self.make(value) with no target -> ObjUtil.cvar(value)
    // The Fantom compiler generates this.make(x) for closure-captured variables
    // IMPORTANT: Do NOT match it-block constructors like `return make { it.x = val }`
    // Cvar wrappers wrap LOCAL VARIABLES, it-block constructors wrap CLOSURES
    if (e.target == null && !e.method.isStatic && e.method.name == "make" && e.args.size == 1)
    {
      arg := e.args.first
      // Only treat as cvar if argument is NOT a closure (closures are it-blocks)
      if (arg.id != ExprId.closure)
      {
        // This is a cvar wrapper - use ObjUtil.cvar() instead of self.make()
        w("ObjUtil.cvar(")
        expr(arg)
        w(")")
        return
      }
      // If argument IS a closure, fall through to handle as constructor call
    }

    // Check if this is a dynamic call (-> operator)
    // Dynamic calls use trap() for runtime dispatch
    if (e.isDynamic)
    {
      w("ObjUtil.trap(")
      if (e.target != null)
        expr(e.target)
      else
        w("self")
      w(", ").str(escapeName(e.name))
      // Fantom semantics: no args = null, with args = list
      if (e.args.isEmpty)
      {
        w(", None)")
      }
      else
      {
        w(", [")
        e.args.each |arg, i|
        {
          if (i > 0) w(", ")
          expr(arg)
        }
        w("])")
      }
      return
    }

    // Check if this is a Func.call() or Func.callList() - convert to direct invocation
    methodParentQname := e.method.parent.qname
    if (methodParentQname == "sys::Func" && (e.method.name == "call" || e.method.name == "callList"))
    {
      // f.call(a, b) -> f(a, b)
      // f.callList([a, b]) -> f(*list)
      if (e.target != null)
      {
        expr(e.target)
      }
      w("(")
      if (e.method.name == "callList" && !e.args.isEmpty)
      {
        // callList takes a list, spread it
        w("*")
        expr(e.args.first)
      }
      else
      {
        e.args.each |arg, i|
        {
          if (i > 0) w(", ")
          expr(arg)
        }
      }
      w(")")
      return
    }

    // Check if this is an Obj method that should use ObjUtil dispatch
    if (e.target != null && isObjUtilMethod(e.method))
    {
      objUtilCall(e)
      return
    }

    // Check if this is a method call on a primitive type (instance method)
    // Static calls (target is StaticTargetExpr) should NOT use primitive dispatch
    if (e.target != null && isPrimitiveType(e.target.ctype) && e.target.id != ExprId.staticTarget)
    {
      // Convert x.method() to Type.method(x)
      primitiveCall(e)
      return
    }

    // NOTE: List and Map use instance method dispatch (like JS transpiler)
    // No special static dispatch block needed - they fall through to normal method calls

    // Method call
    // Check for private methods - they are non-virtual in Fantom
    // Use static dispatch: ClassName.method(self/target, args)
    // BUT: In static context, there's no self - use factory pattern without self
    // NOTE: Constructors (isCtor) become static factories in Python, so don't add self
    if (e.method.isPrivate && !e.method.isStatic && !e.method.isCtor)
    {
      w(e.method.parent.name).w(".").w(escapeName(e.method.name)).w("(")
      if (e.target != null)
      {
        expr(e.target)
      }
      else if (!m.inStaticContext)
      {
        // Only add self if NOT in static context
        w("self")
      }
      // Add comma separator only if we added a target/self AND have args
      if ((e.target != null || !m.inStaticContext) && !e.args.isEmpty) w(", ")
      e.args.each |arg, i|
      {
        if (i > 0) w(", ")
        expr(arg)
      }
      w(")")
      return
    }

    if (e.target != null)
    {
      expr(e.target)
      w(".")
    }
    else if (e.method.isStatic)
    {
      // Static method call without explicit target needs class qualification
      w(e.method.parent.name).w(".")
    }
    else if (m.inStaticContext)
    {
      // In static context (like _static_init), use class name instead of self
      w(e.method.parent.name).w(".")
    }
    else if (e.method.isPrivate && !e.method.isCtor)
    {
      // Private methods are non-virtual in Fantom - use static dispatch
      // Generate: ClassName.method(self, args) instead of self.method(args)
      // NOTE: Constructors (isCtor) become static factories in Python, so don't add self
      w(e.method.parent.name).w(".").w(escapeName(e.method.name)).w("(self")
      if (!e.args.isEmpty) w(", ")
      e.args.each |arg, i|
      {
        if (i > 0) w(", ")
        expr(arg)
      }
      w(")")
      return
    }
    else
    {
      // Instance method call on self
      w("self.")
    }
    w(escapeName(e.method.name))
    w("(")
    e.args.each |arg, i|
    {
      if (i > 0) w(", ")
      expr(arg)
    }
    w(")")
  }

  ** Check if method should be routed through ObjUtil
  ** These are Obj/Num methods that may be called on primitives coerced to Obj or Num
  private Bool isObjUtilMethod(CMethod m)
  {
    parentQname := m.parent.qname
    name := m.name

    // Obj methods (including _-suffixed versions used when name conflicts with Python builtins)
    if (parentQname == "sys::Obj")
    {
      return name == "isImmutable" ||
             name == "toImmutable" ||
             name == "typeof" ||
             name == "compare" ||
             name == "equals" ||
             name == "hash" ||
             name == "hash_" ||
             name == "toStr"
    }

    // Obj methods on Map - route through ObjUtil for proper dispatch
    // The Fantom compiler may resolve hash/equals/etc to Map parent
    // Note: List methods go through primitiveCall which handles them properly
    if (parentQname == "sys::Map")
    {
      if (name == "hash" || name == "hash_" || name == "equals" || name == "compare" || name == "toStr")
        return true
    }

    // Num methods - toFloat/toInt/toDecimal/toLocale may be called on Num-typed values
    if (parentQname == "sys::Num")
    {
      return name == "toFloat" || name == "toInt" || name == "toDecimal" || name == "toLocale"
    }

    // Decimal methods - toLocale may be called on Decimal-typed values
    if (parentQname == "sys::Decimal")
    {
      return name == "toLocale"
    }

    return false
  }

  ** Output ObjUtil method call: x.method() -> ObjUtil.method(x)
  private Void objUtilCall(CallExpr e)
  {
    methodName := e.method.name

    // Convert to snake_case for Python
    pyName := escapeName(methodName)

    w("ObjUtil.").w(pyName).w("(")
    expr(e.target)
    if (!e.args.isEmpty)
    {
      e.args.each |arg|
      {
        w(", ")
        expr(arg)
      }
    }
    w(")")
  }

  ** Check if type is a primitive that needs static method calls
  ** NOTE: List and Map are NOT primitives - they are pure Fantom classes that extend Obj
  ** (with Python ABC interfaces for interop). They use normal instance method dispatch.
  ** See Brian Frank's guidance: primitives are Bool, Int, Float, Str, Func, Err
  private Bool isPrimitiveType(CType? t)
  {
    if (t == null) return false
    sig := t.toNonNullable.signature
    // Only Bool, Int, Float, Str, Decimal are primitives (matches JS transpiler)
    // List and Map are NOT primitives - they use instance method dispatch
    if (sig == "sys::Bool" || sig == "sys::Int" || sig == "sys::Float" || sig == "sys::Str" || sig == "sys::Decimal")
      return true
    return false
  }

  ** Check if type is a hand-written sys type that uses Python @property
  ** Only include types where we've confirmed @property usage for instance fields
  private Bool isHandWrittenSysType(Str qname)
  {
    // Types confirmed to use Python @property decorators (found via grep @property)
    // Note: Buf removed - uses method-style accessors to match Fantom source patterns
    return qname == "sys::Map" ||     // read-write @property (def_, ordered, caseInsensitive)
           qname == "sys::List" ||    // read-write @property (capacity)
           qname == "sys::Type" ||    // read-only @property (root, v, k, params, ret)
           qname == "sys::StrBuf"     // read-only @property (charset)
  }

  ** Check if type is a hand-written sys type that uses method-style setters
  ** These types use field(value) for setting, not field = value
  private Bool usesMethodStyleSetters(Str qname)
  {
    // Types that use def field(self, value=None) pattern for get/set
    return qname == "sys::Log"        // level(newLevel) setter
  }

  ** Get Python wrapper class name for primitive
  ** NOTE: List and Map are NOT primitives - they use instance method dispatch
  private Str primitiveClassName(CType t)
  {
    sig := t.toNonNullable.signature
    if (sig == "sys::Bool") return "Bool"
    if (sig == "sys::Int") return "Int"
    if (sig == "sys::Float") return "Float"
    if (sig == "sys::Decimal") return "Float"  // Decimal uses Float methods in Python
    if (sig == "sys::Str") return "Str"
    return t.name
  }

  ** Output primitive type static method call: x.method() -> Type.method(x)
  private Void primitiveCall(CallExpr e)
  {
    className := primitiveClassName(e.target.ctype)
    methodName := escapeName(e.method.name)

    w(className).w(".").w(methodName).w("(")
    expr(e.target)
    if (!e.args.isEmpty)
    {
      e.args.each |arg|
      {
        w(", ")
        expr(arg)
      }
    }
    w(")")
  }

  ** Generate the body of a safe call using _safe_ as the target variable
  ** This is called from within a lambda wrapper: ((lambda _safe_: None if _safe_ is None else <body>)(target))
  private Void safeCallBody(CallExpr e)
  {
    // Dynamic call (-> operator) with safe nav
    if (e.isDynamic)
    {
      w("ObjUtil.trap(_safe_, ").str(escapeName(e.name))
      if (e.args.isEmpty)
        w(", None)")
      else
      {
        w(", [")
        e.args.each |arg, i|
        {
          if (i > 0) w(", ")
          expr(arg)
        }
        w("])")
      }
      return
    }

    // Primitive type call with safe nav: _safe_.method() -> Type.method(_safe_)
    if (e.target != null && isPrimitiveType(e.target.ctype) && e.target.id != ExprId.staticTarget)
    {
      className := primitiveClassName(e.target.ctype)
      methodName := escapeName(e.method.name)
      w(className).w(".").w(methodName).w("(_safe_")
      if (!e.args.isEmpty)
      {
        e.args.each |arg|
        {
          w(", ")
          expr(arg)
        }
      }
      w(")")
      return
    }

    // ObjUtil method call with safe nav
    if (e.target != null && isObjUtilMethod(e.method))
    {
      pyName := escapeName(e.method.name)
      w("ObjUtil.").w(pyName).w("(_safe_")
      if (!e.args.isEmpty)
      {
        e.args.each |arg|
        {
          w(", ")
          expr(arg)
        }
      }
      w(")")
      return
    }

    // Regular instance method call with safe nav: _safe_.method(args)
    // NOTE: List and Map use instance methods (like JS) - no special static dispatch needed
    w("_safe_.").w(escapeName(e.method.name)).w("(")
    e.args.each |arg, i|
    {
      if (i > 0) w(", ")
      expr(arg)
    }
    w(")")
  }

  ** Generate the body of a safe field access using _safe_ as the target variable
  ** This is called from within a lambda wrapper: ((lambda _safe_: None if _safe_ is None else <body>)(target))
  private Void safeFieldBody(FieldExpr e)
  {
    fieldName := e.field.name

    // useAccessor=false means direct storage access (&field syntax)
    // In Python, backing fields use _fieldName pattern
    if (!e.useAccessor && !e.field.isStatic)
      w("_safe_._").w(escapeName(fieldName))
    else
    {
      w("_safe_.").w(escapeName(fieldName))
      // Instance fields on transpiled types need () for accessor method
      if (!e.field.isStatic)
      {
        parentSig := e.field.parent.qname
        if (!isHandWrittenSysType(parentSig))
          w("()")
      }
    }
  }

  private Void construction(CallExpr e)
  {
    // Constructor call - always use factory pattern: ClassName.make(args)
    // This is needed because Fantom may have multiple constructors with
    // different signatures, but Python __init__ only has one signature.
    // The .make() factory method handles dispatching to the right constructor.
    curPod := m.curType?.pod?.name
    targetPod := e.method.parent.pod.name
    typeName := e.method.parent.name
    methodName := e.method.name

    if (curPod != null && curPod != "sys" && curPod == targetPod)
    {
      // Same pod, non-sys - use dynamic import
      podPath := PyUtil.podImport(targetPod)
      w("__import__('${podPath}.${typeName}', fromlist=['${typeName}']).${typeName}")
    }
    else
    {
      w(typeName)
    }

    // Always call the factory method: .make() or .fromStr() etc.
    // This ensures correct construction even when __init__ has different signature
    factoryName := methodName == "<ctor>" ? "make" : methodName
    w(".").w(escapeName(factoryName))

    w("(")
    e.args.each |arg, i|
    {
      if (i > 0) w(", ")
      expr(arg)
    }
    w(")")
  }

  private Void field(FieldExpr e)
  {
    fieldName := e.field.name

    // Handle safe navigation operator (?.): short-circuit to null if target is null
    // Pattern: ((lambda _safe_: None if _safe_ is None else _safe_.field)(<target>))
    if (e.isSafe && e.target != null)
    {
      w("((lambda _safe_: None if _safe_ is None else ")
      safeFieldBody(e)
      w(")(")
      expr(e.target)
      w("))")
      return
    }

    // Check for List/Map primitive field access (size, isEmpty, etc.)
    // Convert target.size to List.size(target) for proper Python dispatch
    if (e.target != null && isPrimitiveType(e.target.ctype))
    {
      if (fieldName == "size" || fieldName == "isEmpty" || fieldName == "capacity")
      {
        className := primitiveClassName(e.target.ctype)
        w(className).w(".").w(fieldName).w("(")
        expr(e.target)
        w(")")
        return
      }
    }

    // Check for $this field (outer this capture in closures)
    if (fieldName == "\$this")
    {
      // Inside closure, $this refers to outer self
      // Multi-statement closures use _self, inline lambdas use _outer
      if (m.inClosureWithOuter)
        w("_outer")
      else
        w("_self")
      return
    }

    // Check for captured local variable: pattern varName$N
    // Fantom creates synthetic fields like js$0, expected$2 for captured locals
    if (fieldName.contains("\$"))
    {
      idx := fieldName.index("\$")
      if (idx != null && idx < fieldName.size - 1)
      {
        suffix := fieldName[idx+1..-1]
        // Check if suffix is all digits
        if (!suffix.isEmpty && suffix.all |c| { c.isDigit })
        {
          // This is a captured local variable - output just the base name
          // If we are in a closure, we use the base name to capture from outer scope
          baseName := fieldName[0..<idx]
          w(escapeName(baseName))
          return
        }
      }
    }

    if (e.target != null)
    {
      expr(e.target)
      w(".")
    }
    else if (e.field.isStatic)
    {
      // Static field without explicit target - need class prefix
      w(e.field.parent.name).w(".")
    }

    // useAccessor=false means direct storage access (&field syntax)
    // In Python, backing fields use _fieldName pattern
    // Only add underscore prefix for instance fields, not static accessors
    if (!e.useAccessor && !e.field.isStatic)
      w("_").w(escapeName(e.field.name))
    else
    {
      w(escapeName(e.field.name))
      // Static fields always need () - they're class methods
      // Instance fields on hand-written sys types use @property (no parens)
      // Instance fields on transpiled types use accessor methods (need parens)
      if (e.field.isStatic)
      {
        w("()")
      }
      else
      {
        // For instance fields, check if parent type is a hand-written sys type
        // Hand-written types use @property, transpiled types use accessor methods
        parentSig := e.field.parent.qname
        if (!isHandWrittenSysType(parentSig))
          w("()")
      }
    }
  }

//////////////////////////////////////////////////////////////////////////
// Assignment
//////////////////////////////////////////////////////////////////////////

  private Void assign(BinaryExpr e)
  {
    // Special handling for field assignment
    if (e.lhs.id == ExprId.field)
    {
      fieldExpr := e.lhs as FieldExpr

      // When leave=true, the assignment result is used as an expression value.
      // Python doesn't support `=` in expression context, so we use a helper.
      // This mirrors the JS transpiler's IIFE pattern for field assignments.
      if (e.leave)
      {
        w("ObjUtil.setattr_return(")
        if (fieldExpr.target != null)
          expr(fieldExpr.target)
        else
          w("self")
        w(", \"")
        // Use _fieldName for backing storage (non-accessor) or fieldName for accessor
        if (!fieldExpr.useAccessor)
          w("_")
        w(escapeName(fieldExpr.field.name))
        w("\", ")
        expr(e.rhs)
        w(")")
        return
      }

      // Check if we should use accessor (count = 5) vs direct storage (&count = 5)
      if (fieldExpr.useAccessor)
      {
        // Determine whether to use method call syntax or property assignment:
        // - Hand-written sys types (Map, Type, etc.) use @property -> property assignment
        // - Transpiled types use def field(self, _val_=None): -> method call syntax
        // - Types explicitly marked for method-style setters (Log) -> method call syntax
        parentSig := fieldExpr.field.parent.qname
        useMethodCall := usesMethodStyleSetters(parentSig) || !isHandWrittenSysType(parentSig)

        if (useMethodCall)
        {
          // Use method call syntax: target.fieldName(value)
          if (fieldExpr.target != null)
          {
            expr(fieldExpr.target)
            w(".")
          }
          w(escapeName(fieldExpr.field.name))
          w("(")
          expr(e.rhs)
          w(")")
        }
        else
        {
          // Use Python property assignment: self.fieldName = value
          // This works with @property decorated getters/setters on hand-written types
          if (fieldExpr.target != null)
          {
            expr(fieldExpr.target)
            w(".")
          }
          w(escapeName(fieldExpr.field.name))
          w(" = ")
          expr(e.rhs)
        }
      }
      else
      {
        // Direct storage access: self._count = value or ClassName._count for static
        if (fieldExpr.target != null)
        {
          expr(fieldExpr.target)
          w(".")
        }
        else if (fieldExpr.field.isStatic)
        {
          // Static field without explicit target - need class prefix
          w(fieldExpr.field.parent.name).w(".")
        }
        w("_").w(escapeName(fieldExpr.field.name))
        w(" = ")
        expr(e.rhs)
      }
    }
    else
    {
      // Local var assignment - use walrus operator to make it an expression
      // This allows assignment inside function calls, conditions, etc.
      w("(")
      expr(e.lhs)
      w(" := ")
      expr(e.rhs)
      w(")")
    }
  }

//////////////////////////////////////////////////////////////////////////
// Comparison
//////////////////////////////////////////////////////////////////////////

  private Void same(BinaryExpr e)
  {
    // Use ObjUtil.same() for consistent identity semantics
    // Python's 'is' operator is unreliable with interned literals
    w("ObjUtil.same(")
    expr(e.lhs)
    w(", ")
    expr(e.rhs)
    w(")")
  }

  private Void notSame(BinaryExpr e)
  {
    // Use ObjUtil.same() for consistent identity semantics
    w("(not ObjUtil.same(")
    expr(e.lhs)
    w(", ")
    expr(e.rhs)
    w("))")
  }

  private Void cmpNull(UnaryExpr e)
  {
    expr(e.operand)
    w(" is None")
  }

  private Void cmpNotNull(UnaryExpr e)
  {
    expr(e.operand)
    w(" is not None")
  }

//////////////////////////////////////////////////////////////////////////
// Boolean Operators
//////////////////////////////////////////////////////////////////////////

  private Void boolNot(UnaryExpr e)
  {
    w("not ")
    expr(e.operand)
  }

  private Void boolOr(CondExpr e)
  {
    w("(")
    e.operands.each |op, i|
    {
      if (i > 0) w(" or ")
      expr(op)
    }
    w(")")
  }

  private Void boolAnd(CondExpr e)
  {
    w("(")
    e.operands.each |op, i|
    {
      if (i > 0) w(" and ")
      expr(op)
    }
    w(")")
  }

//////////////////////////////////////////////////////////////////////////
// Type Checks
//////////////////////////////////////////////////////////////////////////

  private Void isExpr(TypeCheckExpr e)
  {
    w("ObjUtil.is_(")
    expr(e.target)
    w(", ")
    typeRef(e.check)
    w(")")
  }

  private Void isnotExpr(TypeCheckExpr e)
  {
    w("(not ObjUtil.is_(")
    expr(e.target)
    w(", ")
    typeRef(e.check)
    w("))")
  }

  private Void asExpr(TypeCheckExpr e)
  {
    w("ObjUtil.as_(")
    expr(e.target)
    w(", ")
    typeRef(e.check)
    w(")")
  }

  private Void coerce(TypeCheckExpr e)
  {
    w("ObjUtil.coerce(")
    expr(e.target)
    w(", ")
    typeRef(e.check)
    w(")")
  }

  private Void typeRef(CType t)
  {
    // Sanitize Java FFI types so they're valid Python strings
    // (they'll fail at runtime if actually used, like JS transpiler)
    sig := PyUtil.sanitizeJavaFfi(t.signature)
    str(sig)
  }

//////////////////////////////////////////////////////////////////////////
// Ternary / Elvis
//////////////////////////////////////////////////////////////////////////

  private Void ternary(TernaryExpr e)
  {
    w("(")
    // Handle assignments in ternary using walrus operator
    ternaryBranch(e.trueExpr)
    w(" if ")
    expr(e.condition)
    w(" else ")
    ternaryBranch(e.falseExpr)
    w(")")
  }

  ** Output ternary branch, converting assignments to walrus operator
  private Void ternaryBranch(Expr e)
  {
    // Unwrap coerce if present
    inner := unwrapCoerce(e)

    // If it's an assignment, convert x = val to (x := val)
    if (inner.id == ExprId.assign)
    {
      assign := inner as BinaryExpr
      // For field assignments, fall back to regular expr (can't use walrus)
      if (assign.lhs.id == ExprId.field)
      {
        expr(e)
        return
      }
      // Use walrus operator for local var assignment
      w("(")
      expr(assign.lhs)
      w(" := ")
      expr(assign.rhs)
      w(")")
    }
    else
    {
      expr(e)
    }
  }

  private Void elvis(BinaryExpr e)
  {
    // a ?: b -> (lambda v: v if v is not None else b)(a)
    w("((lambda _v: _v if _v is not None else ")
    expr(e.rhs)
    w(")(")
    expr(e.lhs)
    w("))")
  }

//////////////////////////////////////////////////////////////////////////
// Shortcuts (operators)
//////////////////////////////////////////////////////////////////////////

  private Void shortcut(ShortcutExpr e)
  {
    // First, try operator maps for binary operators
    binaryOp := PyUtil.binaryOperators.get(e.method.qname)
    if (binaryOp != null)
    {
      doShortcutBinaryOp(e, binaryOp)
      return
    }

    // Try unary operators
    unaryOp := PyUtil.unaryOperators.get(e.method.qname)
    if (unaryOp != null)
    {
      w(unaryOp)
      expr(e.target)
      return
    }

    // Fall back to switch for special cases
    op := e.op
    switch (op)
    {
      case ShortcutOp.eq:
        // Check the opToken for == vs !=
        if (e.opToken == Token.notEq)
          doShortcutBinaryOp(e, "!=")
        else
          doShortcutBinaryOp(e, "==")
      case ShortcutOp.cmp:
        // Check the opToken for comparison type
        switch (e.opToken)
        {
          case Token.lt:   comparison(e, "compare_lt")
          case Token.ltEq: comparison(e, "compare_le")
          case Token.gt:   comparison(e, "compare_gt")
          case Token.gtEq: comparison(e, "compare_ge")
          default:         cmp(e)  // <=>
        }
      case ShortcutOp.negate:    w("(-"); expr(e.target); w(")")
      case ShortcutOp.increment: increment(e)
      case ShortcutOp.decrement: decrement(e)
      case ShortcutOp.get:       indexGet(e)
      case ShortcutOp.set:       indexSet(e)
      // Fallback for arithmetic ops if not in map
      case ShortcutOp.plus:      doShortcutBinaryOp(e, "+")
      case ShortcutOp.minus:     doShortcutBinaryOp(e, "-")
      case ShortcutOp.mult:      doShortcutBinaryOp(e, "*")
      case ShortcutOp.div:       divOp(e)  // Use ObjUtil.div for Fantom semantics (truncated)
      case ShortcutOp.mod:       modOp(e)  // Use ObjUtil.mod for Fantom semantics (truncated)
      default:                   w("# TODO: shortcut ${op}")
    }
  }

  private Void doShortcutBinaryOp(ShortcutExpr e, Str op)
  {
    // Check for string + non-string - route to Str.plus for proper type conversion
    // In Fantom, "str" + x always converts x to string
    // Skip for compound assignment - that's handled below with proper assignment semantics
    if (op == "+" && !e.isAssign && isStringPlusNonString(e))
    {
      stringPlusNonString(e)
      return
    }

    // Check for compound assignment (x *= 3 -> x = x * 3)
    if (e.isAssign)
    {
      // Need to assign the result back to target
      // Unwrap coerce to get actual target
      target := unwrapCoerce(e.target)
      if (target.id == ExprId.localVar)
      {
        localExpr := target as LocalVarExpr
        varName := escapeName(localExpr.var.name)
        // Check for string += null pattern on local var
        if (isStringPlusNullAssign(e))
        {
          w("(").w(varName).w(" := Str.plus(").w(varName).w(", ")
          expr(e.args.first)
          w("))")
        }
        else
        {
          w("(").w(varName).w(" := (").w(varName).w(" ").w(op).w(" ")
          expr(e.args.first)
          w("))")
        }
      }
      else if (target.id == ExprId.field)
      {
        // Field assignment - more complex, use direct assignment
        fieldExpr := target as FieldExpr
        escapedName := escapeName(fieldExpr.field.name)
        if (fieldExpr.target != null)
        {
          expr(fieldExpr.target)
          w(".")
        }
        w("_").w(escapedName).w(" = ")
        if (fieldExpr.target != null)
        {
          expr(fieldExpr.target)
          w(".")
        }
        w("_").w(escapedName).w(" ").w(op).w(" ")
        expr(e.args.first)
      }
      else if (target.id == ExprId.shortcut)
      {
        // Index access compound assignment: x[i] += val -> x[i] = x[i] + val
        shortcutTarget := target as ShortcutExpr
        if (shortcutTarget.op == ShortcutOp.get)
        {
          indexCompoundAssign(shortcutTarget, op, e.args.first)
        }
        else
        {
          // Fallback - just do the operation (won't assign)
          w("(")
          expr(e.target)
          w(" ").w(op).w(" ")
          expr(e.args.first)
          w(")")
        }
      }
      else
      {
        // Fallback - just do the operation (won't assign)
        w("(")
        expr(e.target)
        w(" ").w(op).w(" ")
        expr(e.args.first)
        w(")")
      }
    }
    else
    {
      w("(")
      expr(e.target)
      w(" ").w(op).w(" ")
      expr(e.args.first)
      w(")")
    }
  }

  ** Check if this is a string + non-string pattern that needs Str.plus()
  ** In Fantom, string + anything converts the other operand to string
  private Bool isStringPlusNonString(ShortcutExpr e)
  {
    targetSig := e.target?.ctype?.toNonNullable?.signature ?: ""
    argSig := e.args.first?.ctype?.toNonNullable?.signature ?: ""

    // If neither is a string, no special handling needed
    targetIsStr := targetSig == "sys::Str"
    argIsStr := argSig == "sys::Str"

    if (!targetIsStr && !argIsStr) return false

    // If one is string and other is NOT string, use Str.plus for conversion
    if (targetIsStr && !argIsStr) return true
    if (argIsStr && !targetIsStr) return true

    // Both are strings - use native Python concatenation
    return false
  }

  ** Check if this is a string += null compound assignment pattern
  private Bool isStringPlusNullAssign(ShortcutExpr e)
  {
    // Check if RHS is null
    if (e.args.first?.id != ExprId.nullLiteral) return false

    // Check if target is string type
    targetSig := e.target?.ctype?.toNonNullable?.signature ?: ""
    return targetSig == "sys::Str"
  }

  ** Handle string + non-string concatenation using Str.plus()
  private Void stringPlusNonString(ShortcutExpr e)
  {
    w("Str.plus(")
    expr(e.target)
    w(", ")
    expr(e.args.first)
    w(")")
  }

  ** Handle indexed compound assignment: x[i] += val -> x[i] = x[i] + val
  private Void indexCompoundAssign(ShortcutExpr indexExpr, Str op, Expr value)
  {
    // Generate: container[index] = container[index] op value
    // We need to evaluate container and index only once in case they have side effects
    // For simplicity, generate: target[index] = target[index] op value

    expr(indexExpr.target)
    w("[")
    expr(indexExpr.args.first)
    w("] = ")
    expr(indexExpr.target)
    w("[")
    expr(indexExpr.args.first)
    w("] ").w(op).w(" ")
    expr(value)
  }

  private Void comparison(ShortcutExpr e, Str method)
  {
    w("ObjUtil.").w(method).w("(")
    expr(e.target)
    w(", ")
    expr(e.args.first)
    w(")")
  }

  private Void cmp(ShortcutExpr e)
  {
    w("ObjUtil.compare(")
    expr(e.target)
    w(", ")
    expr(e.args.first)
    w(")")
  }

  private Void divOp(ShortcutExpr e)
  {
    // Float division uses Python / directly
    if (e.target?.ctype?.toNonNullable?.signature == "sys::Float")
    {
      doShortcutBinaryOp(e, "/")
      return
    }

    // Int division uses ObjUtil.div for truncated division semantics
    // (Python // is floor division, Fantom uses truncated toward zero)
    if (e.isAssign)
    {
      // Compound assignment: x /= 5 -> x = ObjUtil.div(x, 5)
      target := unwrapCoerce(e.target)
      if (target.id == ExprId.localVar)
      {
        localExpr := target as LocalVarExpr
        varName := escapeName(localExpr.var.name)
        w("(").w(varName).w(" := ObjUtil.div(").w(varName).w(", ")
        expr(e.args.first)
        w("))")
      }
      else
      {
        w("ObjUtil.div(")
        expr(e.target)
        w(", ")
        expr(e.args.first)
        w(")")
      }
    }
    else
    {
      w("ObjUtil.div(")
      expr(e.target)
      w(", ")
      expr(e.args.first)
      w(")")
    }
  }

  private Void modOp(ShortcutExpr e)
  {
    // Use ObjUtil.mod for Fantom-style modulo semantics
    // (truncated division vs Python's floor division)
    if (e.isAssign)
    {
      // Compound assignment: y %= 5 -> y = ObjUtil.mod(y, 5)
      // Unwrap coerce to get actual target
      target := unwrapCoerce(e.target)
      if (target.id == ExprId.localVar)
      {
        localExpr := target as LocalVarExpr
        varName := escapeName(localExpr.var.name)
        w("(").w(varName).w(" := ObjUtil.mod(").w(varName).w(", ")
        expr(e.args.first)
        w("))")
      }
      else
      {
        w("ObjUtil.mod(")
        expr(e.target)
        w(", ")
        expr(e.args.first)
        w(")")
      }
    }
    else
    {
      w("ObjUtil.mod(")
      expr(e.target)
      w(", ")
      expr(e.args.first)
      w(")")
    }
  }

  ** Unwrap coerce expressions to get the underlying expression
  private Expr unwrapCoerce(Expr e)
  {
    if (e.id == ExprId.coerce)
    {
      te := e as TypeCheckExpr
      return unwrapCoerce(te.target)
    }
    return e
  }

  private Void increment(ShortcutExpr e)
  {
    // ++x (pre) returns new value, x++ (post) returns old value
    target := unwrapCoerce(e.target)
    isPost := e.isPostfixLeave

    if (target.id == ExprId.field)
    {
      // Field access - use ObjUtil helper
      fieldExpr := target as FieldExpr
      method := isPost ? "inc_field_post" : "inc_field"
      w("ObjUtil.").w(method).w("(")
      if (fieldExpr.target != null)
        expr(fieldExpr.target)
      else
        w("self")
      w(", \"_").w(escapeName(fieldExpr.field.name)).w("\")")
    }
    else if (target.id == ExprId.shortcut)
    {
      // Index access (list[i]++) - use ObjUtil helper
      shortcutExpr := target as ShortcutExpr
      if (shortcutExpr.op == ShortcutOp.get)
      {
        method := isPost ? "inc_index_post" : "inc_index"
        w("ObjUtil.").w(method).w("(")
        expr(shortcutExpr.target)
        w(", ")
        expr(shortcutExpr.args.first)
        w(")")
      }
      else
      {
        // Other shortcut - fallback
        w("(")
        expr(e.target)
        w(" + 1)")
      }
    }
    else if (target.id == ExprId.localVar)
    {
      // Local variable - use lambda for post-increment, walrus for pre
      localExpr := target as LocalVarExpr
      varName := escapeName(localExpr.var.name)
      if (isPost)
      {
        // x++ returns old value: ((lambda _o: (setattr(...), _o)[1])(...) - but locals don't have setattr
        // Use: ((_old := x, x := x + 1, _old)[2]) - tuple trick
        w("((_old_").w(varName).w(" := ").w(varName).w(", ")
        w(varName).w(" := ").w(varName).w(" + 1, ")
        w("_old_").w(varName).w(")[2])")
      }
      else
      {
        w("(").w(varName).w(" := ").w(varName).w(" + 1)")
      }
    }
    else
    {
      // Fallback - just add 1 (won't assign but won't error)
      w("(")
      expr(e.target)
      w(" + 1)")
    }
  }

  private Void decrement(ShortcutExpr e)
  {
    // --x (pre) returns new value, x-- (post) returns old value
    target := unwrapCoerce(e.target)
    isPost := e.isPostfixLeave

    if (target.id == ExprId.field)
    {
      // Field access - use ObjUtil helper
      fieldExpr := target as FieldExpr
      method := isPost ? "dec_field_post" : "dec_field"
      w("ObjUtil.").w(method).w("(")
      if (fieldExpr.target != null)
        expr(fieldExpr.target)
      else
        w("self")
      w(", \"_").w(escapeName(fieldExpr.field.name)).w("\")")
    }
    else if (target.id == ExprId.shortcut)
    {
      // Index access (list[i]--) - use ObjUtil helper
      shortcutExpr := target as ShortcutExpr
      if (shortcutExpr.op == ShortcutOp.get)
      {
        method := isPost ? "dec_index_post" : "dec_index"
        w("ObjUtil.").w(method).w("(")
        expr(shortcutExpr.target)
        w(", ")
        expr(shortcutExpr.args.first)
        w(")")
      }
      else
      {
        // Other shortcut - fallback
        w("(")
        expr(e.target)
        w(" - 1)")
      }
    }
    else if (target.id == ExprId.localVar)
    {
      // Local variable - use tuple trick for post-decrement
      localExpr := target as LocalVarExpr
      varName := escapeName(localExpr.var.name)
      if (isPost)
      {
        w("((_old_").w(varName).w(" := ").w(varName).w(", ")
        w(varName).w(" := ").w(varName).w(" - 1, ")
        w("_old_").w(varName).w(")[2])")
      }
      else
      {
        w("(").w(varName).w(" := ").w(varName).w(" - 1)")
      }
    }
    else
    {
      // Fallback - just subtract 1 (won't assign but won't error)
      w("(")
      expr(e.target)
      w(" - 1)")
    }
  }

  private Void indexGet(ShortcutExpr e)
  {
    // Check target type for special handling
    targetSig := e.target?.ctype?.toNonNullable?.signature ?: ""
    arg := e.args.first
    argSig := arg.ctype?.toNonNullable?.signature ?: ""

    // String indexing: str[i] returns Int codepoint, str[range] returns substring
    if (targetSig == "sys::Str")
    {
      if (argSig == "sys::Range")
      {
        // str[range] -> Str.get_range(str, range)
        w("Str.get_range(")
        expr(e.target)
        w(", ")
        expr(arg)
        w(")")
      }
      else
      {
        // str[i] -> Str.get(str, i) returns Int codepoint
        w("Str.get(")
        expr(e.target)
        w(", ")
        expr(arg)
        w(")")
      }
      return
    }

    // Check if index is a Range - need to use List.get_range() instead
    if (argSig == "sys::Range")
    {
      // list[range] -> List.get_range(list, range)
      w("List.get_range(")
      expr(e.target)
      w(", ")
      expr(arg)
      w(")")
    }
    else
    {
      expr(e.target)
      w("[")
      expr(arg)
      w("]")
    }
  }

  private Void indexSet(ShortcutExpr e)
  {
    expr(e.target)
    w("[")
    expr(e.args.first)
    w("] = ")
    expr(e.args[1])
  }

//////////////////////////////////////////////////////////////////////////
// Static Targets and Type Literals
//////////////////////////////////////////////////////////////////////////

  private Void staticTarget(StaticTargetExpr e)
  {
    // Check if this is a same-pod type reference (not sys pod)
    // For same-pod types, use a runtime import to avoid circular import issues
    curPod := m.curType?.pod?.name
    targetPod := e.ctype.pod.name

    if (curPod != null && curPod != "sys" && curPod == targetPod)
    {
      // Same pod, non-sys - use dynamic import
      // __import__('fan.testSys.ObjWrapper', fromlist=['ObjWrapper']).ObjWrapper
      typeName := e.ctype.name
      podPath := PyUtil.podImport(targetPod)
      w("__import__('${podPath}.${typeName}', fromlist=['${typeName}']).${typeName}")
    }
    else
    {
      // Different pod or sys pod - just output class name (imported at top)
      w(e.ctype.name)
    }
  }

  private Void typeLiteral(LiteralExpr e)
  {
    // Type literal like Bool# - create a Type instance
    t := e.val as CType
    if (t != null)
    {
      sig := PyUtil.sanitizeJavaFfi(t.signature)
      w("Type.find(").str(sig).w(")")
    }
    else
    {
      w("None")
    }
  }

  private Void slotLiteral(SlotLiteralExpr e)
  {
    // Slot literal like Int#plus - create Method.find() or Field.find()
    parentSig := e.parent.signature
    slotName := escapeName(e.name)  // Convert to snake_case for Python lookup

    // Determine if it's a method or field
    if (e.slot != null && e.slot is CField)
    {
      w("Field.find(").str("${parentSig}.${slotName}").w(")")
    }
    else
    {
      // Default to Method
      w("Method.find(").str("${parentSig}.${slotName}").w(")")
    }
  }

//////////////////////////////////////////////////////////////////////////
// Closures
//////////////////////////////////////////////////////////////////////////

  private Void closure(ClosureExpr e)
  {
    // Check if this closure was already registered during scan phase
    closureId := m.findClosureId(e)
    if (closureId != null)
    {
      // Already emitted as def, just output reference
      w("_closure_${closureId}")
      return
    }

    // Try various fields for closure body
    Block? codeBlock := null
    if (e.doCall != null && e.doCall.code != null)
      codeBlock = e.doCall.code
    else if (e.call != null && e.call.code != null)
      codeBlock = e.call.code
    else if (e.code != null)
      codeBlock = e.code

    if (codeBlock != null)
    {
      stmts := codeBlock.stmts

      // Single-statement closures can use inline lambda
      // Filter out local var decls, synthetic/void return statements
      realStmts := stmts.findAll |s|
      {
        if (s.id == StmtId.returnStmt)
        {
          ret := s as ReturnStmt
          return ret.expr != null
        }
        if (s.id == StmtId.localDef) return false
        return true
      }

      // Check if simple single-expression body (can use lambda)
      // Assignments cannot be in lambdas - they're statements, not expressions
      if (realStmts.size == 1)
      {
        stmt := realStmts.first
        if (stmt.id == StmtId.returnStmt)
        {
          ret := stmt as ReturnStmt
          // Skip if return contains assignment or index set
          if (ret.expr != null && !isAssignmentExpr(ret.expr))
          {
            closureLambda(e) |->| { expr(ret.expr) }
            return
          }
        }
        if (stmt.id == StmtId.expr)
        {
          exprStmt := stmt as ExprStmt
          // Assignments can't be in lambda body (unless we convert them)
          if (!isAssignmentExpr(exprStmt.expr))
          {
            closureLambda(e) |->| { expr(exprStmt.expr) }
            return
          }
          // Check if it's an index set: map[key] = value
          // Can convert to: map.__setitem__(key, value) for lambda
          if (exprStmt.expr.id == ExprId.shortcut)
          {
            se := exprStmt.expr as ShortcutExpr
            if (se.op == ShortcutOp.set && se.args.size == 2)
            {
              closureLambda(e) |->|
              {
                expr(se.target)
                w(".__setitem__(")
                expr(se.args.first)  // key
                w(", ")
                expr(se.args[1])     // value
                w(")")
              }
              return
            }
          }
        }
      }
    }

    // Fallback - wrap with Func.make_closure() even when body not handled
    // This ensures ALL closures have bind(), params(), etc. (consistent with JS transpiler)
    closureLambda(e) |->| { none }
  }

  ** Generate lambda with outer self capture if needed
  ** Uses Func.make_closure() for proper Fantom Func methods (bind, params, etc.)
  private Void closureLambda(ClosureExpr e, |->| body)
  {
    // Check if closure captures outer this (has $this field)
    needsOuter := e.cls?.fieldDefs?.any |f| { f.name == "\$this" } ?: false

    // Get type info from signature
    sig := e.signature as FuncType

    // Determine immutability from compiler analysis
    immutCase := m.closureImmutability(e)

    // Generate Func.make_closure(spec, lambda)
    w("Func.make_closure({")

    // Returns type
    retType := sig?.returns?.signature ?: "sys::Void"
    w("\"returns\": ").str(retType).w(", ")

    // Immutability case from compiler analysis
    w("\"immutable\": ").str(immutCase).w(", ")

    // Params (sanitize Java FFI type signatures)
    w("\"params\": [")
    if (e.doCall?.params != null)
    {
      e.doCall.params.each |p, i|
      {
        if (i > 0) w(", ")
        pSig := PyUtil.sanitizeJavaFfi(p.type.signature)
        w("{\"name\": ").str(p.name).w(", \"type\": ").str(pSig).w("}")
      }
    }
    else if (sig != null && !sig.params.isEmpty)
    {
      sig.params.each |p, i|
      {
        if (i > 0) w(", ")
        name := sig.names.getSafe(i) ?: "_p${i}"
        pSig := PyUtil.sanitizeJavaFfi(p.signature)
        w("{\"name\": ").str(name).w(", \"type\": ").str(pSig).w("}")
      }
    }
    w("]}, ")

    // Lambda body
    if (needsOuter)
    {
      w("(lambda ")
      closureParams(e)
      w(", _outer=self: ")
      m.inClosureWithOuter = true
      body()
      m.inClosureWithOuter = false
      w(")")
    }
    else
    {
      w("(lambda ")
      closureParams(e)
      w(": ")
      body()
      w(")")
    }

    w(")")  // Close Func.make_closure()
  }

  ** Check if expression is an assignment (can't be in lambda body)
  ** Note: Increment/decrement CAN be in lambdas because they transpile to
  ** ObjUtil.incField()/decField() which are function calls returning values
  private Bool isAssignmentExpr(Expr e)
  {
    // Direct assignment
    if (e.id == ExprId.assign) return true

    // Index set (list[i] = x)
    if (e.id == ExprId.shortcut)
    {
      se := e as ShortcutExpr
      if (se.op == ShortcutOp.set) return true
      // Compound assignment (x += 5), but NOT increment/decrement
      // Increment/decrement transpile to ObjUtil.incField() which returns a value
      if (se.isAssign && se.op != ShortcutOp.increment && se.op != ShortcutOp.decrement)
        return true
    }

    // Check wrapped in coerce
    if (e.id == ExprId.coerce)
    {
      tc := e as TypeCheckExpr
      return isAssignmentExpr(tc.target)
    }

    return false
  }

  private Void closureParams(ClosureExpr e)
  {
    // Get the signature - this is the EXPECTED type (what the target method wants)
    // which may have fewer params than declared in source code (Fantom allows coercion)
    sig := e.signature as FuncType
    expectedParamCount := sig?.params?.size ?: 0

    // Use doCall.params for parameter names, but LIMIT to expected count
    // This handles cases where closure declares extra params that get coerced away
    // ALL params get =None default because Python (unlike JS) requires all args
    // JS: f(a,b) called as f() gives a=undefined, b=undefined
    // Python: f(a,b) called as f() raises TypeError
    if (e.doCall?.params != null && !e.doCall.params.isEmpty)
    {
      // Only output up to expectedParamCount params (or all if signature unavailable)
      maxParams := expectedParamCount > 0 ? expectedParamCount : e.doCall.params.size
      actualCount := e.doCall.params.size.min(maxParams)

      actualCount.times |i|
      {
        if (i > 0) w(", ")
        w(escapeName(e.doCall.params[i].name)).w("=None")
      }

      // If no params were output but we need at least one for lambda syntax
      // Use _=None so it doesn't require an argument
      if (actualCount == 0 && expectedParamCount == 0)
        w("_=None")
    }
    // Fallback to signature for it-blocks with implicit it
    else
    {
      if (sig != null && !sig.params.isEmpty)
      {
        // Check if this is an it-block (uses implicit it)
        if (e.isItBlock)
        {
          w("it=None")
        }
        else
        {
          sig.names.each |name, i|
          {
            if (i > 0) w(", ")
            if (name.isEmpty)
              w("_p${i}=None")
            else
              w(escapeName(name)).w("=None")
          }
        }
      }
      else
      {
        w("_=None")  // Lambda needs placeholder but shouldn't require arg
      }
    }
  }
}
