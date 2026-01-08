//
// Copyright (c) 2025, Brian Frank and Andy Frank
// Licensed under the Academic Free License version 3.0
//
// History:
//   Dec 2025  Creation
//

using compiler

**
** Python statement printer
**
class PyStmtPrinter : PyPrinter
{
  new make(PyPrinter parent) : super.make(parent.m.out)
  {
    this.m = parent.m
    this.exprPrinter = PyExprPrinter(this)
  }

  private PyExprPrinter exprPrinter

  ** Print an expression
  Void expr(Expr e) { exprPrinter.expr(e) }

  ** Print a statement
  Void stmt(Stmt s)
  {
    // Check if we need to emit closures before this statement
    emitPendingClosuresForStatement()

    switch (s.id)
    {
      case StmtId.nop:          return  // no-op
      case StmtId.expr:         exprStmt(s)
      case StmtId.localDef:     localDef(s)
      case StmtId.ifStmt:       ifStmt(s)
      case StmtId.returnStmt:   returnStmt(s)
      case StmtId.throwStmt:    throwStmt(s)
      case StmtId.forStmt:      forStmt(s)
      case StmtId.whileStmt:    whileStmt(s)
      case StmtId.breakStmt:    w("break").eos
      case StmtId.continueStmt: continueStmt()
      case StmtId.tryStmt:      tryStmt(s)
      case StmtId.switchStmt:   switchStmt(s)
      default:
        w("# TODO: stmt ${s.id}").eos
    }
  }

//////////////////////////////////////////////////////////////////////////
// Method-Level Closure Scanning
//////////////////////////////////////////////////////////////////////////

  ** Scan entire method body for multi-statement closures
  Void scanMethodForClosures(Block b)
  {
    // Use index to track statement location
    b.stmts.each |s, idx|
    {
      m.stmtIndex = idx
      scanStmt(s)
    }
  }

  ** Recursively scan a statement for closure expressions
  private Void scanStmt(Stmt s)
  {
    switch (s.id)
    {
      case StmtId.expr:
        exprStmt := s as ExprStmt
        scanExprForClosures(exprStmt.expr)
      case StmtId.localDef:
        localDef := s as LocalDefStmt
        if (localDef.init != null)
          scanExprForClosures(localDef.init)
      case StmtId.ifStmt:
        ifStmt := s as IfStmt
        scanExprForClosures(ifStmt.condition)
        scanInnerBlockForClosures(ifStmt.trueBlock)
        if (ifStmt.falseBlock != null)
          scanInnerBlockForClosures(ifStmt.falseBlock)
      case StmtId.returnStmt:
        ret := s as ReturnStmt
        if (ret.expr != null)
          scanExprForClosures(ret.expr)
      case StmtId.throwStmt:
        throwStmt := s as ThrowStmt
        scanExprForClosures(throwStmt.exception)
      case StmtId.whileStmt:
        whileStmt := s as WhileStmt
        scanExprForClosures(whileStmt.condition)
        scanInnerBlockForClosures(whileStmt.block)
      case StmtId.forStmt:
        forStmt := s as ForStmt
        if (forStmt.init != null) scanStmt(forStmt.init)
        if (forStmt.condition != null) scanExprForClosures(forStmt.condition)
        if (forStmt.update != null) scanExprForClosures(forStmt.update)
        if (forStmt.block != null) scanInnerBlockForClosures(forStmt.block)
      case StmtId.tryStmt:
        tryStmt := s as TryStmt
        scanInnerBlockForClosures(tryStmt.block)
        tryStmt.catches.each |c| { scanInnerBlockForClosures(c.block) }
        if (tryStmt.finallyBlock != null)
          scanInnerBlockForClosures(tryStmt.finallyBlock)
      case StmtId.switchStmt:
        switchStmt := s as SwitchStmt
        scanExprForClosures(switchStmt.condition)
        switchStmt.cases.each |c| { scanInnerBlockForClosures(c.block) }
        if (switchStmt.defaultBlock != null)
          scanInnerBlockForClosures(switchStmt.defaultBlock)
    }
  }

  ** Scan inner block (don't increment method stmtIndex)
  private Void scanInnerBlockForClosures(Block b)
  {
    b.stmts.each |s| { scanStmt(s) }
  }

  ** Recursively scan an expression for closures
  private Void scanExprForClosures(Expr e)
  {
    // Check if this is a closure that needs extraction
    if (e.id == ExprId.closure)
    {
      ce := e as ClosureExpr
      if (isMultiStatementClosure(ce))
      {
        // Only register closures at method level (depth == 0)
        // Nested closures (depth > 0) will be emitted inline in parent closure
        if (m.closureDepth == 0)
        {
          // Find existing or register new closure
          closureId := m.findClosureId(ce)
          if (closureId == null)
          {
            closureId = m.nextClosureId
            m.pendingClosures.add([ce, closureId])
            m.registeredClosures.add([ce, closureId])
          }

          // Record first usage location if not already recorded
          if (!m.closureFirstUse.containsKey(closureId))
          {
            m.closureFirstUse[closureId] = m.stmtIndex
          }
        }
      }
    }

    // Recursively scan child expressions
    scanExprChildren(e)
  }

  ** Scan children of an expression
  private Void scanExprChildren(Expr e)
  {
    switch (e.id)
    {
      case ExprId.call:
        ce := e as CallExpr
        if (ce.target != null) scanExprForClosures(ce.target)
        ce.args.each |arg| { scanExprForClosures(arg) }
      case ExprId.construction:
        // Constructor calls - scan args for closures
        ce := e as CallExpr
        ce.args.each |arg| { scanExprForClosures(arg) }
      case ExprId.listLiteral:
        // List literals can contain closures
        le := e as ListLiteralExpr
        le.vals.each |val| { scanExprForClosures(val) }
      case ExprId.mapLiteral:
        // Map literals can contain closures in values
        me := e as MapLiteralExpr
        me.keys.each |key| { scanExprForClosures(key) }
        me.vals.each |val| { scanExprForClosures(val) }
      case ExprId.shortcut:
        se := e as ShortcutExpr
        if (se.target != null) scanExprForClosures(se.target)
        se.args.each |arg| { scanExprForClosures(arg) }
      case ExprId.ternary:
        te := e as TernaryExpr
        scanExprForClosures(te.condition)
        scanExprForClosures(te.trueExpr)
        scanExprForClosures(te.falseExpr)
      case ExprId.boolOr:
        co := e as CondExpr
        co.operands.each |op| { scanExprForClosures(op) }
      case ExprId.boolAnd:
        ca := e as CondExpr
        ca.operands.each |op| { scanExprForClosures(op) }
      case ExprId.coerce:
        tc := e as TypeCheckExpr
        scanExprForClosures(tc.target)
      case ExprId.assign:
        be := e as BinaryExpr
        scanExprForClosures(be.lhs)
        scanExprForClosures(be.rhs)
      case ExprId.elvis:
        ee := e as BinaryExpr
        scanExprForClosures(ee.lhs)
        scanExprForClosures(ee.rhs)
      case ExprId.closure:
        // Scan INSIDE the closure body for nested closures
        // Increment depth so nested closures won't be registered at method level
        cl := e as ClosureExpr
        Block? codeBlock := null
        if (cl.doCall != null && cl.doCall.code != null)
          codeBlock = cl.doCall.code
        else if (cl.call != null && cl.call.code != null)
          codeBlock = cl.call.code
        else if (cl.code != null)
          codeBlock = cl.code
        if (codeBlock != null)
        {
          m.closureDepth++
          scanInnerBlockForClosures(codeBlock)
          m.closureDepth--
        }
      // Field, localVar, literals etc have no children with closures
    }
  }

  ** Scan a closure body for nested multi-statement closures and register them
  ** This allows nested closures to be emitted as defs before being used
  private Void scanClosureBodyForNestedClosures(ClosureExpr ce)
  {
    codeBlock := ce.doCall?.code ?: ce.code
    if (codeBlock == null) return

    // Scan each statement, tracking index for closure emission
    codeBlock.stmts.each |s, idx|
    {
      m.stmtIndex = idx
      scanStmtForNestedClosures(s)
    }
  }

  ** Scan a statement for nested closures (registers them for emission)
  private Void scanStmtForNestedClosures(Stmt s)
  {
    switch (s.id)
    {
      case StmtId.expr:
        exprStmt := s as ExprStmt
        scanExprForNestedClosures(exprStmt.expr)
      case StmtId.localDef:
        localDef := s as LocalDefStmt
        if (localDef.init != null)
          scanExprForNestedClosures(localDef.init)
      case StmtId.returnStmt:
        ret := s as ReturnStmt
        if (ret.expr != null)
          scanExprForNestedClosures(ret.expr)
      case StmtId.ifStmt:
        ifStmt := s as IfStmt
        scanExprForNestedClosures(ifStmt.condition)
        ifStmt.trueBlock.stmts.each |st| { scanStmtForNestedClosures(st) }
        if (ifStmt.falseBlock != null)
          ifStmt.falseBlock.stmts.each |st| { scanStmtForNestedClosures(st) }
      case StmtId.whileStmt:
        whileStmt := s as WhileStmt
        scanExprForNestedClosures(whileStmt.condition)
        whileStmt.block.stmts.each |st| { scanStmtForNestedClosures(st) }
      case StmtId.forStmt:
        forStmt := s as ForStmt
        if (forStmt.init != null) scanStmtForNestedClosures(forStmt.init)
        if (forStmt.condition != null) scanExprForNestedClosures(forStmt.condition)
        if (forStmt.update != null) scanExprForNestedClosures(forStmt.update)
        if (forStmt.block != null) forStmt.block.stmts.each |st| { scanStmtForNestedClosures(st) }
    }
  }

  ** Scan an expression for nested closures (registers them)
  ** Only registers IMMEDIATE nested closures - deeper nesting will be handled
  ** recursively when each nested closure writes its own body
  private Void scanExprForNestedClosures(Expr e)
  {
    if (e.id == ExprId.closure)
    {
      ce := e as ClosureExpr
      if (isMultiStatementClosure(ce))
      {
        // Register for emission inside parent closure
        closureId := m.findClosureId(ce)
        if (closureId == null)
        {
          closureId = m.nextClosureId
          m.pendingClosures.add([ce, closureId])
          m.registeredClosures.add([ce, closureId])
        }
        if (!m.closureFirstUse.containsKey(closureId))
        {
          m.closureFirstUse[closureId] = m.stmtIndex
        }
      }

      // DON'T recursively scan inside - that will happen when writeClosure
      // processes this closure's body and calls scanClosureBodyForNestedClosures
      return
    }

    // Scan children (but not inside closures - handled above)
    scanExprChildrenForNestedClosures(e)
  }

  ** Scan children of an expression for nested closures
  private Void scanExprChildrenForNestedClosures(Expr e)
  {
    switch (e.id)
    {
      case ExprId.call:
        ce := e as CallExpr
        if (ce.target != null) scanExprForNestedClosures(ce.target)
        ce.args.each |arg| { scanExprForNestedClosures(arg) }
      case ExprId.construction:
        ce := e as CallExpr
        ce.args.each |arg| { scanExprForNestedClosures(arg) }
      case ExprId.shortcut:
        se := e as ShortcutExpr
        if (se.target != null) scanExprForNestedClosures(se.target)
        se.args.each |arg| { scanExprForNestedClosures(arg) }
      case ExprId.ternary:
        te := e as TernaryExpr
        scanExprForNestedClosures(te.condition)
        scanExprForNestedClosures(te.trueExpr)
        scanExprForNestedClosures(te.falseExpr)
      case ExprId.boolOr:
        co := e as CondExpr
        co.operands.each |op| { scanExprForNestedClosures(op) }
      case ExprId.boolAnd:
        ca := e as CondExpr
        ca.operands.each |op| { scanExprForNestedClosures(op) }
      case ExprId.coerce:
        tc := e as TypeCheckExpr
        scanExprForNestedClosures(tc.target)
      case ExprId.assign:
        be := e as BinaryExpr
        scanExprForNestedClosures(be.lhs)
        scanExprForNestedClosures(be.rhs)
      case ExprId.elvis:
        ee := e as BinaryExpr
        scanExprForNestedClosures(ee.lhs)
        scanExprForNestedClosures(ee.rhs)
    }
  }

  ** Check if a closure requires multi-statement def extraction
  private Bool isMultiStatementClosure(ClosureExpr ce)
  {
    // Check all possible code block locations (matching PyExprPrinter)
    Block? codeBlock := null
    if (ce.doCall != null && ce.doCall.code != null)
      codeBlock = ce.doCall.code
    else if (ce.call != null && ce.call.code != null)
      codeBlock = ce.call.code
    else if (ce.code != null)
      codeBlock = ce.code

    if (codeBlock == null) return false

    stmts := codeBlock.stmts

    // Check if closure has local variable declarations
    hasLocalVars := stmts.any |s| { s.id == StmtId.localDef }
    if (hasLocalVars) return true

    // Check if closure has assignments (can't be in lambda body)
    hasAssign := stmts.any |s|
    {
      if (s.id == StmtId.expr)
      {
        es := s as ExprStmt
        return es.expr.id == ExprId.assign
      }
      if (s.id == StmtId.returnStmt)
      {
        ret := s as ReturnStmt
        return ret.expr?.id == ExprId.assign
      }
      return false
    }
    if (hasAssign) return true

    // Check if closure has control flow statements that can't be in lambda body
    // These include if, switch, for, while, try - they have nested blocks
    hasControlFlow := stmts.any |s|
    {
      s.id == StmtId.ifStmt ||
      s.id == StmtId.switchStmt ||
      s.id == StmtId.forStmt ||
      s.id == StmtId.whileStmt ||
      s.id == StmtId.tryStmt
    }
    if (hasControlFlow) return true

    // Count real statements (excluding synthetic returns)
    realStmtCount := 0
    stmts.each |s|
    {
      if (s.id == StmtId.returnStmt)
      {
        ret := s as ReturnStmt
        if (ret.expr != null) realStmtCount++
      }
      else if (s.id != StmtId.nop)
      {
        realStmtCount++
      }
    }

    return realStmtCount > 1
  }

//////////////////////////////////////////////////////////////////////////
// Closure Emission
//////////////////////////////////////////////////////////////////////////

  ** Emit any pending closures that are first used in the current statement
  private Void emitPendingClosuresForStatement()
  {
    if (m.pendingClosures.isEmpty) return

    // Find closures to emit for this statement
    toEmit := [,]
    remaining := [,]

    m.pendingClosures.each |item|
    {
      data := item as Obj[]
      closureId := data[1] as Int
      firstUse := m.closureFirstUse[closureId]

      // Emit if this is the first use statement, OR if usage wasn't tracked (fallback)
      if (firstUse == m.stmtIndex || firstUse == null)
        toEmit.add(item)
      else
        remaining.add(item)
    }

    if (toEmit.isEmpty) return

    // Update pending list
    m.pendingClosures = remaining

    // Emit closures
    toEmit.each |item|
    {
      data := item as Obj[]
      ce := data[0] as ClosureExpr
      closureId := data[1] as Int
      writeClosure(ce, closureId)
    }
  }

  ** Write a multi-statement closure as a def function
  private Void writeClosure(ClosureExpr ce, Int closureId)
  {
    // def _closure_N(params, _self=self):
    w("def _closure_${closureId}(")

    // Get the signature - this is the EXPECTED type (what the target method wants)
    // which may have fewer params than declared in source code (Fantom allows coercion)
    sig := ce.signature as FuncType
    expectedParamCount := sig?.params?.size ?: 0

    // Parameters from closure's doCall method - these have the actual names
    // from the source code, but LIMIT to expected count from signature
    // ALL params get =None default because Python (unlike JS) requires all args
    // JS: f(a,b) called as f() gives a=undefined, b=undefined
    // Python: f(a,b) called as f() raises TypeError
    hasParams := false
    if (ce.doCall?.params != null && !ce.doCall.params.isEmpty)
    {
      // Only output up to expectedParamCount params (or all if signature unavailable)
      maxParams := expectedParamCount > 0 ? expectedParamCount : ce.doCall.params.size
      actualCount := ce.doCall.params.size.min(maxParams)

      actualCount.times |i|
      {
        if (i > 0) w(", ")
        w(escapeName(ce.doCall.params[i].name)).w("=None")
        hasParams = true
      }
    }
    else
    {
      // Fallback to signature names (for it-blocks with implicit it)
      // sig was already defined above
      if (sig != null && !sig.params.isEmpty)
      {
        // Check if this is an it-block (uses implicit it)
        if (ce.isItBlock)
        {
          w("it=None")
          hasParams = true
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
            hasParams = true
          }
        }
      }
    }

    // Add _self=self for outer self capture if needed
    needsOuter := ce.cls?.fieldDefs?.any |f| { f.name == "\$this" } ?: false
    if (needsOuter)
    {
      if (hasParams) w(", ")
      w("_self=self")
    }

    w(")").colon
    indent

    // Multi-statement closures use _self=self, not _outer=self
    // Ensure the flag is false so $this references output _self
    m.inClosureWithOuter = false

    // Set wrapped closure flag - closures can use wrapper variables from outer scope
    // This tells localVar() to use wrapper names when resolving variables
    wasInWrappedClosure := m.inWrappedClosure
    m.inWrappedClosure = !m.paramWrappers.isEmpty

    // Save method-level closure state - nested closures have their own scope
    savedPending := m.pendingClosures.dup
    savedFirstUse := m.closureFirstUse.dup
    savedStmtIndex := m.stmtIndex
    m.pendingClosures = [,]
    m.closureFirstUse = [:]

    // Scan and register nested closures for emission inside this closure
    // This ensures nested defs are written before they're referenced
    scanClosureBodyForNestedClosures(ce)

    // Write the closure body
    codeBlock := ce.doCall?.code ?: ce.code
    hasContent := false
    if (codeBlock != null && !codeBlock.stmts.isEmpty)
    {
      codeBlock.stmts.each |s, idx|
      {
        // Skip self-referential captured variable assignments (js$0 = js$0 -> js = js)
        // Python captures variables automatically from the enclosing scope
        if (isCapturedVarSelfAssign(s)) return

        // Track statement index for nested closure emission
        m.stmtIndex = idx

        // Note: inClosureWithOuter stays false for multi-statement closures
        // because they use _self=self parameter, not _outer=self
        stmt(s)
        hasContent = true
      }
    }

    // Restore method-level closure state
    m.pendingClosures = savedPending
    m.closureFirstUse = savedFirstUse
    m.stmtIndex = savedStmtIndex

    if (!hasContent)
    {
      pass
    }

    // Restore wrapped closure flag
    m.inWrappedClosure = wasInWrappedClosure

    unindent
    nl

    // Wrap the closure with Func.make_closure for proper Fantom Func methods
    w("_closure_${closureId} = Func.make_closure({")

    // Returns type
    retType := sig?.returns?.signature ?: "sys::Void"
    w("\"returns\": ").str(retType).w(", ")

    // Immutability case from compiler analysis
    immutCase := m.closureImmutability(ce)
    w("\"immutable\": ").str(immutCase).w(", ")

    // Params
    w("\"params\": [")
    if (ce.doCall?.params != null)
    {
      maxParams := expectedParamCount > 0 ? expectedParamCount : ce.doCall.params.size
      actualCount := ce.doCall.params.size.min(maxParams)
      actualCount.times |i|
      {
        if (i > 0) w(", ")
        p := ce.doCall.params[i]
        w("{\"name\": ").str(p.name).w(", \"type\": ").str(p.type.signature).w("}")
      }
    }
    else if (sig != null && !sig.params.isEmpty)
    {
      sig.params.each |p, i|
      {
        if (i > 0) w(", ")
        name := sig.names.getSafe(i) ?: "_p${i}"
        w("{\"name\": ").str(name).w(", \"type\": ").str(p.signature).w("}")
      }
    }
    w("]}, _closure_${closureId})").eos
  }

  ** Check if statement is a self-referential captured variable assignment
  ** These are generated by Fantom compiler like: js$0 = js$0
  ** Python captures variables automatically so we skip these
  private Bool isCapturedVarSelfAssign(Stmt s)
  {
    // Must be expression statement
    if (s.id != StmtId.expr) return false

    exprStmt := s as ExprStmt

    // Must be assignment expression
    if (exprStmt.expr.id != ExprId.assign) return false

    assign := exprStmt.expr as BinaryExpr

    // Both sides must be field expressions
    if (assign.lhs.id != ExprId.field || assign.rhs.id != ExprId.field) return false

    lhsField := assign.lhs as FieldExpr
    rhsField := assign.rhs as FieldExpr

    // Both must reference the same captured variable field (pattern: name$N)
    lhsName := lhsField.field.name
    rhsName := rhsField.field.name

    if (lhsName != rhsName) return false

    // Check if it's a captured variable pattern (name$N where N is digits)
    if (!lhsName.contains("\$")) return false

    idx := lhsName.index("\$")
    if (idx == null || idx >= lhsName.size - 1) return false

    suffix := lhsName[idx+1..-1]
    return !suffix.isEmpty && suffix.all |c| { c.isDigit }
  }

//////////////////////////////////////////////////////////////////////////
// Block
//////////////////////////////////////////////////////////////////////////

  ** Print a block of statements
  ** Handles "effectively empty" blocks (all nops or catch vars) by adding pass
  Void block(Block? b, Bool isCatchBlock := false)
  {
    indent

    hasContent := false
    if (b != null && !b.stmts.isEmpty)
    {
      b.stmts.each |s|
      {
        // Skip nops - they produce no output
        if (s.id == StmtId.nop) return

        // In catch blocks, skip catch variable declarations (handled by except...as)
        if (isCatchBlock && s.id == StmtId.localDef && (s as LocalDefStmt).isCatchVar) return

        stmt(s)
        hasContent = true
      }
    }

    // Python requires content in blocks - add pass if effectively empty
    if (!hasContent)
      pass

    unindent
  }

//////////////////////////////////////////////////////////////////////////
// Statements
//////////////////////////////////////////////////////////////////////////

  private Void exprStmt(ExprStmt s)
  {
    expr(s.expr)
    eos
  }

  private Void localDef(LocalDefStmt s)
  {
    // Skip catch vars - handled in tryStmt
    if (s.isCatchVar) return

    // Skip captured variable self-assignments (js = js$0 -> js = js)
    // Python captures variables automatically from enclosing scope
    if (isCapturedVarLocalDef(s)) return

    // Check if this is a cvar wrapper definition: varName_Wrapper = ObjUtil.cvar(paramName)
    // Record the mapping for closure variable resolution
    detectAndRecordWrapper(s)

    w(escapeName(s.name))
    if (s.init != null)
    {
      w(" = ")
      // If init is an assignment, only output the RHS
      if (s.init.id == ExprId.assign)
      {
        assign := s.init as BinaryExpr
        expr(assign.rhs)
      }
      else
      {
        expr(s.init)
      }
    }
    else
    {
      w(" = None")
    }
    eos
  }

  ** Detect if this is a cvar wrapper definition and record the mapping
  ** Pattern: x_Wrapper = ObjUtil.cvar(x) or xWrapper = ObjUtil.cvar(x)
  private Void detectAndRecordWrapper(LocalDefStmt s)
  {
    if (s.init == null) return

    // Unwrap coerces and assignments to get the actual call
    initExpr := s.init
    while (initExpr.id == ExprId.coerce)
    {
      tc := initExpr as TypeCheckExpr
      initExpr = tc.target
    }
    if (initExpr.id == ExprId.assign)
    {
      assign := initExpr as BinaryExpr
      initExpr = assign.rhs
      while (initExpr.id == ExprId.coerce)
      {
        tc := initExpr as TypeCheckExpr
        initExpr = tc.target
      }
    }

    // Check if it's a call expression (for self.make pattern)
    if (initExpr.id != ExprId.call) return

    call := initExpr as CallExpr

    // Pattern: self.make(x) - this is the cvar wrapper constructor
    // The transpiler converts this to ObjUtil.cvar(x)
    if (call.method.name == "make" && call.target == null && !call.method.isStatic && call.args.size == 1)
    {
      // This is a cvar wrapper - extract the wrapped variable name
      arg := call.args.first

      // Unwrap coerces on the argument
      while (arg.id == ExprId.coerce)
      {
        tc := arg as TypeCheckExpr
        arg = tc.target
      }

      // The argument should be a local variable reference
      if (arg.id == ExprId.localVar)
      {
        localArg := arg as LocalVarExpr
        paramName := localArg.var.name
        wrapperName := s.name  // The name of the wrapper variable being defined

        // Record the mapping: paramName -> wrapperName
        m.recordWrapper(paramName, wrapperName)
      }
    }
  }

  ** Check if this localDef is a captured variable initialization
  ** Pattern: js := assign(field(js$0)) where js$0 is a captured variable field
  private Bool isCapturedVarLocalDef(LocalDefStmt s)
  {
    if (s.init == null) return false

    // Unwrap coerce expressions to get to the actual content
    initExpr := s.init
    while (initExpr.id == ExprId.coerce)
    {
      tc := initExpr as TypeCheckExpr
      initExpr = tc.target
    }

    // Check if init is assignment - get the RHS
    if (initExpr.id == ExprId.assign)
    {
      assign := initExpr as BinaryExpr
      initExpr = assign.rhs
      // Unwrap coerce on RHS too
      while (initExpr.id == ExprId.coerce)
      {
        tc := initExpr as TypeCheckExpr
        initExpr = tc.target
      }
    }

    // Check if we have a field reference to a captured variable
    if (initExpr.id != ExprId.field) return false

    fieldExpr := initExpr as FieldExpr
    fieldName := fieldExpr.field.name

    // Check if field name matches pattern: varName$N
    if (!fieldName.contains("\$")) return false

    idx := fieldName.index("\$")
    if (idx == null || idx >= fieldName.size - 1) return false

    baseName := fieldName[0..<idx]
    suffix := fieldName[idx+1..-1]

    // Suffix must be all digits
    if (suffix.isEmpty || !suffix.all |c| { c.isDigit }) return false

    // Base name must match the local variable being defined
    return baseName == s.name
  }

  private Void ifStmt(IfStmt s)
  {
    w("if ")
    expr(s.condition)
    colon
    block(s.trueBlock)
    if (s.falseBlock != null)
    {
      w("else")
      colon
      block(s.falseBlock)
    }
  }

  private Void returnStmt(ReturnStmt s)
  {
    if (s.expr != null)
    {
      // Unwrap coerces to check for assignment
      unwrapped := unwrapCoerce(s.expr)

      // Handle return with assignment: return x = 5 -> x = 5; return x
      if (unwrapped.id == ExprId.assign)
      {
        assign := unwrapped as BinaryExpr
        // Execute assignment first
        expr(s.expr)
        eos
        // Then return the value
        w("return ")
        // Return the LHS (the variable that now holds the assigned value)
        // This avoids re-evaluating the RHS which may have side effects
        expr(assign.lhs)
        eos
        return
      }

      // Handle return with compound assignment: return x += 5 -> x += 5; return x
      if (unwrapped.id == ExprId.shortcut)
      {
        shortcut := unwrapped as ShortcutExpr
        if (shortcut.isAssign)
        {
          // Execute assignment first
          expr(s.expr)
          eos
          // Then return the target (the updated value)
          w("return ")
          expr(shortcut.target)
          eos
          return
        }
      }
    }

    w("return")
    if (s.expr != null)
    {
      w(" ")
      expr(s.expr)
    }
    eos
  }

  ** Unwrap coerce expressions
  private Expr unwrapCoerce(Expr e)
  {
    if (e.id == ExprId.coerce)
    {
      tc := e as TypeCheckExpr
      return unwrapCoerce(tc.target)
    }
    return e
  }

  private Void throwStmt(ThrowStmt s)
  {
    w("raise ")
    expr(s.exception)
    eos
  }

  private Void forStmt(ForStmt s)
  {
    // Fantom for loop: for (init; cond; update)
    // Python equivalent: init; while cond: block; update
    //
    // IMPORTANT: We track the update expression so that continue statements
    // inside the loop body can emit it before jumping. Otherwise continue
    // would skip the update and cause an infinite loop.
    if (s.init != null) stmt(s.init)
    w("while ")
    if (s.condition != null)
      expr(s.condition)
    else
      w("True")
    colon
    indent

    // Set forLoopUpdate so continue statements know to emit it
    savedUpdate := m.forLoopUpdate
    m.forLoopUpdate = s.update

    if (s.block != null)
      s.block.stmts.each |st| { stmt(st) }

    // Restore previous update (for nested for loops)
    m.forLoopUpdate = savedUpdate

    if (s.update != null)
    {
      expr(s.update)
      eos
    }
    unindent
  }

  ** Handle continue statement - must emit for loop update expression first
  private Void continueStmt()
  {
    // If we're in a for loop with an update expression, emit it before continue
    // This prevents infinite loops where continue skips the i++ update
    if (m.forLoopUpdate != null)
    {
      expr(m.forLoopUpdate)
      eos
    }
    w("continue").eos
  }

  private Void whileStmt(WhileStmt s)
  {
    w("while ")
    expr(s.condition)
    colon
    block(s.block)
  }

  private Void tryStmt(TryStmt s)
  {
    w("try")
    colon
    block(s.block)

    s.catches.each |c|
    {
      w("except")
      if (c.errType != null)
      {
        w(" ")
        w(c.errType.name)
      }
      else
      {
        w(" Exception")
      }
      if (c.errVariable != null)
      {
        w(" as ").w(escapeName(c.errVariable))
      }
      colon
      block(c.block, true)  // isCatchBlock=true for catch variable handling
    }

    if (s.finallyBlock != null)
    {
      w("finally")
      colon
      block(s.finallyBlock)
    }
  }

  private Void switchStmt(SwitchStmt s)
  {
    // Python doesn't have switch, use if/elif/else
    // IMPORTANT: Evaluate condition once to avoid side effects being repeated
    // (e.g., switch(i++) must only increment i once)
    switchVarId := m.nextSwitchVarId
    w("_switch_${switchVarId} = ")
    expr(s.condition)
    eos

    first := true
    s.cases.each |c|
    {
      if (first)
      {
        w("if ")
        first = false
      }
      else
      {
        w("elif ")
      }

      // Match any of the case values against the cached condition
      c.cases.each |e, i|
      {
        if (i > 0) w(" or ")
        w("(")
        w("_switch_${switchVarId}")
        w(" == ")
        expr(e)
        w(")")
      }
      colon
      block(c.block)
    }

    if (s.defaultBlock != null)
    {
      if (!first) w("else")
      else w("if True")
      colon
      block(s.defaultBlock)
    }
  }
}
