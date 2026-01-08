#
# util::NativeConsole - Native Python implementation
# Hand-written runtime for Python transpilation
#

import sys
from fan.sys.Obj import Obj
from fan.sys.Type import Type


class NativeConsole(Obj):
    """
    Native console implementation for Python.
    Wraps Python's print/input for console I/O.
    """

    # Singleton instance
    _curNative = None

    def __init__(self):
        super().__init__()
        self._indent = 0

    @staticmethod
    def cur_native():
        """Get the default console singleton."""
        if NativeConsole._curNative is None:
            NativeConsole._curNative = NativeConsole()
        return NativeConsole._curNative

    def typeof(self):
        return Type.find("util::NativeConsole")

    def width(self):
        """Number of chars that fit horizontally in console or null if unknown."""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.columns
        except:
            return None

    def height(self):
        """Number of lines that fit vertically in console or null if unknown."""
        try:
            import shutil
            size = shutil.get_terminal_size()
            return size.lines
        except:
            return None

    def debug(self, msg, err=None):
        """Print a message at the debug level."""
        self._print_msg("DEBUG", msg, err)
        return self

    def info(self, msg, err=None):
        """Print a message at the informational level."""
        self._print_msg(None, msg, err)
        return self

    def warn(self, msg, err=None):
        """Print a message at the warning level."""
        self._print_msg("WARN", msg, err)
        return self

    def err(self, msg, err=None):
        """Print a message at the error level."""
        self._print_msg("ERR", msg, err, file=sys.stderr)
        return self

    def _print_msg(self, level, msg, err, file=None):
        """Internal helper to print messages."""
        if file is None:
            file = sys.stdout

        indent_str = "  " * self._indent

        if level:
            print(f"{indent_str}{level}: {msg}", file=file)
        else:
            print(f"{indent_str}{msg}", file=file)

        if err is not None:
            try:
                trace = err.trace_to_str()
                for line in str(trace).splitlines():
                    if level:
                        print(f"{indent_str}{level}: {line}", file=file)
                    else:
                        print(f"{indent_str}{line}", file=file)
            except:
                print(f"{indent_str}  {err}", file=file)

    def table(self, obj):
        """Print tabular data to the console."""
        # Import ConsoleTable dynamically to avoid circular imports
        try:
            ConsoleTable = __import__('fan.util.ConsoleTable', fromlist=['ConsoleTable']).ConsoleTable
            t = ConsoleTable.make(obj)
            t.dump(self)
        except Exception as e:
            # Fallback: just print the object
            self.info(str(obj))
        return self

    def clear(self):
        """Clear the console of all text if supported."""
        # ANSI escape code to clear screen
        print("\033[2J\033[H", end="")
        return self

    def group(self, msg, collapsed=False):
        """Enter an indented group level in the console."""
        self.info(msg)
        self._indent += 1
        return self

    def group_end(self):
        """Exit an indented group level."""
        if self._indent > 0:
            self._indent -= 1
        return self

    def prompt(self, msg=""):
        """Prompt the user to enter a string from standard input."""
        try:
            return input(msg)
        except EOFError:
            return None

    def prompt_password(self, msg=""):
        """Prompt the user to enter a password with echo disabled."""
        try:
            import getpass
            return getpass.getpass(msg)
        except EOFError:
            return None
        except Exception:
            # Fallback if getpass doesn't work (e.g., no tty)
            return self.prompt(msg)
