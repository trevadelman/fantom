#
# Copyright (c) 2025, Brian Frank and Andy Frank
# Licensed under the Academic Free License version 3.0
#

from .Obj import Obj
from .ObjUtil import ObjUtil


class CvarWrapper:
    """Wrapper for closure-captured variables (cvars).

    When a closure modifies a local variable, the transpiler wraps
    the variable in a CvarWrapper so modifications are visible outside
    the closure.
    """
    __slots__ = ('_val',)

    def __init__(self, val=None):
        self._val = val


class Test(Obj):
    """Base class for unit tests"""

    def __init__(self):
        super().__init__()
        self._verifyCount = 0
        self._curTestMethod = None
        self._tempDir = None

    def make(self, val=None):
        """Create a cvar wrapper for closure-captured variables.

        The transpiler generates self.make(value) to wrap variables
        that are captured and modified by closures.
        """
        return CvarWrapper(val)

    def verifyCount(self):
        return self._verifyCount

    def curTestMethod(self):
        return self._curTestMethod

    def verify(self, cond, msg=None):
        if not cond:
            self.fail(msg)
        self._verifyCount += 1

    def verifyTrue(self, cond, msg=None):
        return self.verify(cond, msg)

    def verifyFalse(self, cond, msg=None):
        if cond:
            self.fail(msg)
        self._verifyCount += 1

    def verifyNull(self, a, msg=None):
        if a is not None:
            if msg is None:
                msg = f"{ObjUtil.toStr(a)} is not null"
            self.fail(msg)
        self._verifyCount += 1

    def verifyNotNull(self, a, msg=None):
        if a is None:
            if msg is None:
                msg = "null"
            self.fail(msg)
        self._verifyCount += 1

    def verifyEq(self, expected, actual, msg=None):
        if not ObjUtil.equals(expected, actual):
            if msg is None:
                msg = f"{ObjUtil.toStr(expected)} != {ObjUtil.toStr(actual)}"
            self.fail(msg)
        self._verifyCount += 1

    def verifyNotEq(self, expected, actual, msg=None):
        if ObjUtil.equals(expected, actual):
            if msg is None:
                msg = f"{ObjUtil.toStr(expected)} == {ObjUtil.toStr(actual)}"
            self.fail(msg)
        self._verifyCount += 1

    def verifySame(self, expected, actual, msg=None):
        if not ObjUtil.same(expected, actual):
            if msg is None:
                msg = f"{ObjUtil.toStr(expected)} !== {ObjUtil.toStr(actual)}"
            self.fail(msg)
        self._verifyCount += 1

    def verifyNotSame(self, expected, actual, msg=None):
        if ObjUtil.same(expected, actual):
            if msg is None:
                msg = f"{ObjUtil.toStr(expected)} === {ObjUtil.toStr(actual)}"
            self.fail(msg)
        self._verifyCount += 1

    def verifyType(self, obj, t):
        self.verifyEq(ObjUtil.typeof(obj), t)

    def verifyErr(self, errType, func):
        try:
            func()
        except Exception as e:
            # For now, just verify an error was thrown
            # TODO: Check errType matches
            self._verifyCount += 1
            return
        self.fail(f"No err thrown, expected {errType}")

    def verifyErrMsg(self, errType, errMsg, func):
        try:
            func()
        except Exception as e:
            # Verify error message matches
            self._verifyCount += 1
            actual_msg = str(e) if not hasattr(e, "msg") else e.msg()
            self.verifyEq(errMsg, actual_msg)
            return
        self.fail(f"No err thrown, expected {errType}")

    def fail(self, msg=None):
        if msg is None:
            raise AssertionError("Test failed")
        else:
            raise AssertionError(f"Test failed: {msg}")

    def setup(self):
        """Called before each test method"""
        pass

    def teardown(self):
        """Called after each test method"""
        pass

    def tempDir(self):
        """Get/create temporary test directory.

        Returns a File representing a clean temporary directory
        that can be used for test file operations. The directory
        is created fresh for each test run.
        """
        if self._tempDir is None:
            import tempfile
            import shutil
            import os
            from .File import File

            # Create test subdirectory in system temp
            base = tempfile.gettempdir()
            test_path = os.path.join(base, "fantest")

            # Clean existing and create fresh
            if os.path.exists(test_path):
                shutil.rmtree(test_path)
            os.makedirs(test_path)

            # Return as File
            self._tempDir = File.os(test_path + os.sep)

        return self._tempDir
