import sys
import os
import textwrap
import shutil
import re
import types
import inspect
import io
from collections import namedtuple, defaultdict


class clex(Exception):
	pass


__long_commands = dict()
__short_commands = dict()
__commands = list()
__arguments = list()

__checks = list()
__help_printers = list()


def __check():
	pass


def print_help(f=sys.stdout):
	def translate_annotation(v):

		if v.annotation == inspect._empty: return ""
		return ":" + v.annotation.__name__

	line_width = 80
	if f == sys.stdout or f == sys.stderr:
		line_width = shutil.get_terminal_size((line_width, 20)).columns

	wrap = textwrap.TextWrapper(width=line_width, tabsize=2)
	appname = os.path.split(sys.argv[0])[1]

	f.write(f"{appname} [options]")
	for arg in __arguments:
		params = inspect.signature(arg).parameters
		f.write(f" {arg.ident}")
		if len(params) == 1:
			k, v = tuple(params.items())[0]
			f.write(translate_annotation(v))
		else:
			f.write(":(")
			f.write(" ".join(k + translate_annotation(v) for k, v in params.items()))
			f.write(")")
		if arg.repeated:
			f.write("...")
	f.write("\n")

	main = __import__("__main__")
	if main.__doc__ is not None:
		wrap.initial_indent = wrap.subsequent_indent = '  '
		f.write(wrap.fill(main.__doc__) + "\n")

	wrap.initial_indent = wrap.subsequent_indent = '    '
	for arg in __arguments:
		if arg.__doc__ is None: continue
		f.write(f"  {arg.ident}\n")
		f.write(wrap.fill(arg.__doc__) + "\n")

	f.write("Options:\n")

	wrap.initial_indent = wrap.subsequent_indent = '    '
	for cmd in __commands:
		if cmd.shortname is not None and cmd.longname is not None:
			f.write(f"  -{cmd.shortname}|--{cmd.longname}")
		elif cmd.shortname is not None:
			f.write(f"  -{cmd.shortname}")
		else:
			f.write(f"  --{cmd.longname}")

		params = inspect.signature(cmd).parameters

		for k, v in params.items():
			f.write(f" {k}{translate_annotation(v)}")
		f.write("\n")
		if cmd.__doc__ is not None:
			f.write(wrap.fill(cmd.__doc__) + "\n")

	wrap.initial_indent = wrap.subsequent_indent = '  '
	for printer in __help_printers:
		buf = io.StringIO()
		printer(buf)
		for ln in buf.getvalue().splitlines():
			ln = ln.rstrip()
			lns = ln.lstrip()
			wrap.initial_indent = wrap.subsequent_indent = ln[:len(ln) - len(lns)]
			f.write(wrap.fill(lns) + "\n")


def command(short, long=None):
	def wrapper(func):
		longname = long
		if short is None and long is None:
			longname = func.__name__
		func.shortname = short
		func.longname = longname

		if longname is None:
			func.ident = "-" + short
		else:
			func.ident = "--" + longname

		if short is not None:
			global __short_commands
			if short in __short_commands:
				raise SyntaxError(f"command shorthand {short} redefined")
			__short_commands[short] = func

		if longname is not None:
			global __long_commands
			if longname in __long_commands:
				raise SyntaxError(f"command switch {longname} redefined")
			__long_commands[longname] = func

		global __commands
		__commands.append(func)
		return func

	if isinstance(short, types.FunctionType):
		func = short
		short = None
		return wrapper(func)

	if len(short) != 1:
		raise SyntaxError(
		  f"invalid command shortname ({short}) - must be a single character")

	return wrapper


def argument(dummy=None, repeated=False, name=None):
	def wrapper(func):
		global __arguments

		if len(__arguments) > 0 and __arguments[-1].repeated:
			raise SyntaxError("argument added after repeated argument")

		params = inspect.signature(func).parameters
		if len(params) < 1:
			raise SyntaxError("argument handlers must take at least one argument")

		func.repeated = repeated
		if name is not None:
			func.ident = name
		else:
			func.ident = func.__name__

		__arguments.append(func)
		return func

	if isinstance(dummy, types.FunctionType):
		return wrapper(dummy)

	return wrapper


def check(func):
	global __checks
	__checks.append(func)
	return func


def help_printer(func):
	global __help_printers
	__help_printers.append(func)
	return func


@command("h", "help")
def _():
	"""Print this help text and exit normally"""
	print_help(sys.stdout)
	sys.exit(0)


def process(argv=sys.argv):
	wysiwyg = False

	i_argument = 0
	subcommand = None
	subparams = None
	subargs = list()

	def set_command(cmd):
		params = inspect.signature(cmd).parameters
		if len(params) < 1:
			cmd()
			return None, None

		subargs.clear()
		return cmd, tuple(params.items())

	def get_argument():
		if i_argument < len(__arguments):
			return set_command(__arguments[i_argument])

		if len(__arguments) > 0 and __arguments[-1].repeated:
			return set_command(__arguments[-1])

		return None, None

	try:

		for arg in argv[1:]:
			if subcommand is not None:
				key, param = subparams[len(subargs)]

			if not wysiwyg and arg == "--options":
				if subcommand is not None:
					if hasattr(subcommand, "options"):
						print(" ".join(getattr(subcommand, "options")(*subargs)))
					if hasattr(param, "options"):
						print(" ".join(param.options()))
				else:
					for id in __short_commands:
						print("-" + id)
					for id in __long_commands:
						print("--" + id)
				sys.exit(0)

			if not wysiwyg and arg[:1] == "-":
				if arg == "--":
					wysiwyg = True
					continue

				if arg[:2] == "--":
					id = arg[2:]
					if not id in __long_commands:
						raise clex(f"unknown switch: --{id}")
					subcommand, subparams = set_command(__long_commands[id])
					continue
				else:
					for id in arg[1:]:
						if not id in __short_commands:
							raise clex(f"unknown switch: -{id}")
						subcommand, subparams = set_command(__short_commands[id])
					continue
			elif subcommand is None:
				subcommand, subparams = get_argument()
				if subcommand is None:
					raise clex(f"stray argument: {arg}")
				i_argument += 1

			if subcommand is not None:
				key, param = subparams[len(subargs)]
				annot = param.annotation
				newarg = arg
				if annot != inspect._empty:
					try:
						newarg = annot(arg)
					except ValueError as e:
						raise clex(
						  f"invalid argument for {subcommand.ident}'s '{key} param: {e}")

				subargs.append(newarg)
				if len(subargs) == len(subparams):
					subcommand(*subargs)
					subcommand = None

		if subcommand is not None:
			raise clex(
			  f"missing argument(s) for {subcommand.ident}: {', '.join(k for k,v in subparams[len(subargs):])}"
			)

		for check in __checks:
			check()

	except clex as e:
		print_help(sys.stderr)
		sys.stderr.write(f"\x1b[31;1mError\x1b[30;0m: {e}\n")
		sys.exit(1)


class Bool:
	def __init__(s, v):
		v = v.lower()
		if v in {"on", "1", "yes", "y", "true", "t"}:
			s._value = True
		elif v in {"off", "0", "no", "n", "false", "f"}:
			s._value = False
		else:
			raise ValueError(f"not a Bool: '{v}'")

	@property
	def value(s):
		return s._value

	@classmethod
	def options(cls):
		return ("on", "1", "yes", "y", "true", "t", "off", "0", "no", "n", "false",
		        "f")


class Flag:
	def __init__(s, short, long, description=None):
		s._value = False

		@command(short, long)
		def _():
			s._value = True

		_.__doc__ = description

	@property
	def value(s):
		return s._value

	def __bool__(s):
		return s._value


class FlagCount:
	def __init__(s, short, long, description=None):
		s._value = 0

		@command(short, long)
		def _():
			s._value += 1

		_.__doc__ = description

	@property
	def value(s):
		return s._value

	def __bool__(s):
		return s._value > 0


class Variable:
	def __init__(s, type, default, short, long, description=None):
		s._value = default

		@command(short, long)
		def _(v: type):
			s._value = v

		_.__doc__ = description

	@property
	def value(s):
		return s._value


class VariableList:
	def __init__(s, type, short, long, description=None):
		s._values = list()

		@command(short, long)
		def _(v: type):
			s._values.append(v)

		_.__doc__ = description

	@property
	def values(s):
		return s._values


class ArgVariable:
	def __init__(s, type, default, name, description=None, required=False):
		s._value = default
		s._default = default
		s._isset = False
		s._name = name

		@argument(name=name)
		def _(v: type):
			s._value = v
			s._isset = True

		if required:

			@check
			def _():
				if not s._isset:
					raise clex(f"{s._name} not set")

		_.__doc__ = description

	@property
	def value(s):
		return s._value


class ArgListVariable:
	def __init__(s, type, name, description=None, required=False):
		s._values = list()
		s._name = name
		s._type = type

		@argument(name=name, repeated=True)
		def _(v: type):
			s._values.append(v)

		if required:

			@check
			def _():
				if len(s._values) < 1:
					raise clex(f"{s._name} not set")

		_.__doc__ = description

	@property
	def values(s):
		return s._values


def file_path(s):
	"""path to an existing file in the file system"""

	if not os.path.exists(s):
		raise ValueError(f"file does not exist: {s}")

	if not os.path.isfile(os.path.realpath(s)):
		raise ValueError(f"path target is not a file: {s}")

	return s


def dir_path(s):
	"""path to an existing directory in the file system"""

	if not os.path.exists(s):
		raise ValueError(f"file does not exist: {s}")

	if not os.path.isdir(os.path.realpath(s)):
		raise ValueError(f"path target is not a directory: {s}")

	return s


def new_dir_path(s):
	"""path to an existing directory or a viable new directory in the file system"""

	if os.path.exists(s):
		if not os.path.isdir(os.path.realpath(s)):
			raise ValueError(f"path target is not a directory: {s}")

	return s


def new_file_path(s):
	"""path to an existing directory or a viable new directory in the file system"""

	if os.path.exists(s):
		if not os.path.isfile(os.path.realpath(s)):
			raise ValueError(f"path target is not a file: {s}")

	return s


def werror(v: str):
	sys.stderr.write(f"\x1b[31;1mError\x1b[30;0m: {v}\n")


def wwarn(v: str):
	sys.stderr.write(f"\x1b[33;1mWarning\x1b[30;0m: {v}\n")


e_escape = re.compile(b"\x1b("
                      b"\\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]" # CSI sequence
                      b")")


class TablePrinter:
	cell_t = namedtuple("cell_t", "content width")

	def __init__(s, firstRowHeader=True, columnSeparator=" "):
		s._rows = list()
		s._nColumns = 0
		s._nRows = 0
		s._columnWidths = defaultdict(lambda: 0)
		s._dirty = False
		s._text = ""

		s.firstRowHeader = firstRowHeader
		s.columnSeparator = columnSeparator

	def renderRow(s, i_row):
		row = s._rows[i_row]

		res = ""
		col = 0

		for cell in row:
			res += cell.content + " " * (s._columnWidths[col] - cell.width)
			col += 1
			if col < s._nColumns: res += s.columnSeparator

		while col + 1 < s._nColumns:
			res += " " * s._columnWidths[col] + s.columnSeparator
			col += 1
		if col < s.nColumns:
			res += " " * s._columnWidths[col]
			col += 1
		res += "\n"
		return res

	def renderSeparator(s):
		res = ""
		if s._nColumns > 0:
			for i in range(s._nColumns - 1):
				res += "-" * (s._columnWidths[i] + len(s.columnSeparator))
			res += "-" * s._columnWidths[s.nColumns - 1]

		res += "\n"
		return res

	def addRow(s, *cells):
		s._rows.append(
		  tuple(
		    s.cell_t(v, len(e_escape.sub(b"", v.encode()).decode()))
		    for v in (str(w) for w in cells)))

		fullRerender = False
		if len(cells) > s._nColumns:
			fullRerender = True
			s._nColumns = len(cells)

		oldWidths = tuple(sorted(s._columnWidths.items()))

		for i, cell in enumerate(s._rows[-1]):
			s._columnWidths[i] = max(s._columnWidths[i], cell.width)

		if tuple(sorted(s._columnWidths.items())) != oldWidths:
			fullRerender = True

		if fullRerender:
			s._dirty = True
		elif not s._dirty:
			s._text += s.renderRow(len(s._rows) - 1)

	def render(s, force=False):
		if not force and not s._dirty: return
		s._text = ""
		if len(s._rows) < 1: return

		s._text = s.renderRow(0)

		if s.firstRowHeader:
			s._text += s.renderSeparator

		for i in range(1, len(s._rows)):
			s._text += s.renderRow(i)

	@property
	def nColumns(s):
		return s._nColumns

	@property
	def nRows(s):
		return len(s._rows)

	def __str__(s):
		s.render()

		return s._text
