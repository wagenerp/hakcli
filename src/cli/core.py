import sys
import os
import textwrap
import shutil
import re
import types
import inspect
import io
from collections import namedtuple, defaultdict
from . import util


class clex(Exception):
	pass


class CLINode:
	def __init__(s, name, description=None, parent=None):
		s.name = name
		s.description = description
		s.parent = parent
		s.long_commands = dict()
		s.long_commands = dict()
		s.short_commands = dict()
		s.subcommand_map = dict()
		s.commands = list()
		s.subcommands = list()
		s.arguments = list()
		s.help_printers = list()
		s.checks = list()
		s.instantiated = False

		s.properties = dict()

	def __getattr__(s, k):
		return s.properties[k]()

	def hasShortCommand(s, short):
		if short in s.short_commands: return True
		if s.parent is not None:
			if s.parent.hasShortCommand(short): return True
		return False

	def hasLongCommand(s, long):
		if long in s.long_commands: return True
		if s.parent is not None:
			if s.parent.hasLongCommand(long): return True
		return False

	def __bool__(s):
		return s.instantiated

	def command(s, short, long=None):
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
				if s.hasShortCommand(short):
					raise SyntaxError(f"command shorthand {short} redefined")
				s.short_commands[short] = func

			if longname is not None:
				if s.hasLongCommand(longname):
					raise SyntaxError(f"command switch {longname} redefined")
				s.long_commands[longname] = func

			s.commands.append(func)
			return func

		if isinstance(short, types.FunctionType):
			func = short
			short = None
			return wrapper(func)

		if len(short) != 1:
			raise SyntaxError(
			  f"invalid command shortname ({short}) - must be a single character")

		return wrapper

	def argument(s, dummy=None, repeated=False, name=None):
		def wrapper(func):

			if len(s.arguments) > 0 and s.arguments[-1].repeated:
				raise SyntaxError("argument added after repeated argument")

			params = inspect.signature(func).parameters
			if len(params) < 1:
				raise SyntaxError("argument handlers must take at least one argument")

			func.repeated = repeated
			if name is not None:
				func.ident = name
			else:
				func.ident = func.__name__

			s.arguments.append(func)
			return func

		if isinstance(dummy, types.FunctionType):
			return wrapper(dummy)

		return wrapper

	def subcommand(s, name, description=None, useParent=False):
		if name in s.subcommands:
			raise SyntaxError(f"subcommand {name} redefined")
		scmd = CLINode(name, description, parent=s if useParent else None)
		s.subcommand_map[name] = scmd
		s.subcommands.append(scmd)
		return scmd

	def check(s, func):
		s.checks.append(func)
		return func

	def help_printer(s, func):
		s.help_printers.append(func)
		return func

	def process(s, argv=sys.argv):
		wysiwyg = False

		i_argument = 0
		subcommand = None
		subparams = None
		subargs = list()

		s.instantiated = True

		def set_command(cmd):
			params = inspect.signature(cmd).parameters
			if len(params) < 1:
				cmd()
				return None, None

			subargs.clear()
			return cmd, tuple(params.items())

		def get_argument():
			if i_argument < len(s.arguments):
				return set_command(s.arguments[i_argument])

			if len(s.arguments) > 0 and s.arguments[-1].repeated:
				return set_command(s.arguments[-1])

			return None, None

		try:

			for iarg, arg in enumerate(argv[1:], 1):
				if subcommand is not None:
					key, param = subparams[len(subargs)]

				if not wysiwyg and arg == "--options":
					if subcommand is not None:
						if hasattr(subcommand, "options"):
							print(" ".join(getattr(subcommand, "options")(*subargs)))
						if hasattr(param, "options"):
							print(" ".join(param.options()))
					else:
						for id in s.short_commands:
							print("-" + id)
						for id in s.long_commands:
							print("--" + id)
					sys.exit(0)

				if not wysiwyg and arg[:1] == "-":
					if arg == "--":
						wysiwyg = True
						continue

					if arg[:2] == "--":
						id = arg[2:]
						if not id in s.long_commands:
							raise clex(f"unknown switch: --{id}")
						subcommand, subparams = set_command(s.long_commands[id])
						continue
					else:
						for id in arg[1:]:
							if not id in s.short_commands:
								raise clex(f"unknown switch: -{id}")
							subcommand, subparams = set_command(s.short_commands[id])
						continue
				elif subcommand is None:
					if arg in s.subcommand_map:
						s.subcommand_map[arg].process(argv[iarg:])
						break
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

			for check in s.checks:
				check()

		except clex as e:
			print_help(sys.stderr)
			sys.stderr.write(f"\x1b[31;1mError\x1b[30;0m: {e}\n")
			sys.exit(1)

	def print_help(s, f=sys.stdout, indent=0):
		def translate_annotation(v):

			if v.annotation == inspect._empty: return ""
			return ":" + v.annotation.__name__

		line_width = 80
		if f == sys.stdout or f == sys.stderr:
			line_width = shutil.get_terminal_size((line_width, 20)).columns

		P0 = util.WrappedPrinter(f, indent + 0)
		PS0 = util.WrappedPrinter(f, indent + (1 if indent > 0 else 0))
		PS1 = util.WrappedPrinter(f, indent + (2 if indent > 0 else 1))
		PS2 = util.WrappedPrinter(f, indent + (3 if indent > 0 else 2))

		with P0 as p:
			p += f"{s.name}"
			if len(s.commands) > 0:
				p += " [options]"
			for arg in s.arguments:
				params = inspect.signature(arg).parameters
				p += f" {arg.ident}"
				if len(params) == 1:
					k, v = tuple(params.items())[0]
					p += (translate_annotation(v))
				else:
					p += ":("
					p += " ".join(k + translate_annotation(v) for k, v in params.items())
					p += ")"
				if arg.repeated:
					p += "..."

		if s.description is not None:
			PS0 *= s.description

		for arg in s.arguments:
			if arg.__doc__ is None: continue
			PS1 *= arg.ident
			PS2 *= arg.__doc__

		if len(s.commands) > 0:
			PS0 *= "Options:"

			for cmd in s.commands:
				with PS1 as p:
					if cmd.shortname is not None and cmd.longname is not None:
						p += f"-{cmd.shortname}|--{cmd.longname}"
					elif cmd.shortname is not None:
						p += f"-{cmd.shortname}"
					else:
						p += f"--{cmd.longname}"

					params = inspect.signature(cmd).parameters

					for k, v in params.items():
						p += f" {k}{translate_annotation(v)}"

				if cmd.__doc__ is not None:
					PS2 *= cmd.__doc__

		if len(s.subcommands) > 0:
			PS0 *= "Subcommands:"
			for scmd in s.subcommands:
				scmd.print_help(f, PS1.indent)

		wrap = textwrap.TextWrapper(width=line_width, tabsize=2)
		for printer in s.help_printers:
			buf = io.StringIO()
			printer(buf)
			for ln in buf.getvalue().splitlines():
				ln = ln.rstrip()
				lns = ln.lstrip()
				wrap.initial_indent = wrap.subsequent_indent = ln[:len(ln) - len(lns)]
				f.write(wrap.fill(lns) + "\n")

	def Flag(s, short, long, description=None):
		class Flag:
			def __init__(s, owner, short, long, description=None):
				s._value = False

				@owner.command(short, long)
				def _():
					s._value = True

				_.__doc__ = description

			@property
			def value(s):
				return s._value

			def __bool__(s):
				return s._value

		res = Flag(s, short, long, description)
		s.properties[long] = lambda: res.value
		return res

	def FlagCount(s, short, long, description=None):
		class FlagCount:
			def __init__(s, owner, short, long, description=None):
				s._value = 0

				@owner.command(short, long)
				def _():
					s._value += 1

				_.__doc__ = description

			@property
			def value(s):
				return s._value

			def __bool__(s):
				return s._value > 0

		res = FlagCount(s, short, long, description=None)
		s.properties[long] = lambda: res.value
		return res

	def Variable(s, type, default, short, long, description=None):
		class Variable:
			def __init__(s, owner, type, default, short, long, description=None):
				s._value = default

				@owner.command(short, long)
				def _(v: type):
					s._value = v

				_.__doc__ = description

			@property
			def value(s):
				return s._value

		res = Variable(s, type, default, short, long, description)
		s.properties[long] = lambda: res.value
		return res

	def VariableList(s, type, short, long, description=None):
		class VariableList:
			def __init__(s, owner, type, short, long, description=None):
				s._values = list()

				@owner.command(short, long)
				def _(v: type):
					s._values.append(v)

				_.__doc__ = description

			@property
			def values(s):
				return s._values

		res = VariableList(s, type, short, long, description)
		s.properties[long] = lambda: res.values
		return res

	def ArgVariable(s, type, default, name, description=None, required=False):
		ss = s

		class ArgVariable:
			def __init__(s,
			             owner,
			             type,
			             default,
			             name,
			             description=None,
			             required=False):
				s._value = default
				s._default = default
				s._isset = False
				s._name = name

				@owner.argument(name=name)
				def _(v: type):
					s._value = v
					s._isset = True

				if required:

					@ss.check
					def _():
						if not s._isset:
							raise clex(f"{s._name} not set")

				_.__doc__ = description

			@property
			def value(s):
				return s._value

		res = ArgVariable(s, type, default, name, description, required)
		s.properties[name] = lambda: res.value
		return res

	def ArgListVariable(s, type, name, description=None, required=False):
		ss = s

		class ArgListVariable:
			def __init__(s, owner, type, name, description=None, required=False):
				s._values = list()
				s._name = name
				s._type = type

				@owner.argument(name=name, repeated=True)
				def _(v: type):
					s._values.append(v)

				if required:

					@ss.check
					def _():
						if len(s._values) < 1:
							raise clex(f"{s._name} not set")

				_.__doc__ = description

			@property
			def values(s):
				return s._values

		res = ArgListVariable(s, type, name, description, required)
		s.properties[name] = lambda: res.values
		return res


main = __import__("__main__")
root = CLINode(os.path.split(sys.argv[0])[1], main.__doc__)

command = root.command
argument = root.argument
subcommand = root.subcommand
process = root.process
check = root.check
help_printer = root.help_printer
print_help = root.print_help

Flag = root.Flag
FlagCount = root.FlagCount
Variable = root.Variable
VariableList = root.VariableList
ArgVariable = root.ArgVariable
ArgListVariable = root.ArgListVariable


@command("h", "help")
def _():
	"""Print this help text and exit normally"""
	print_help(sys.stdout)
	sys.exit(0)
