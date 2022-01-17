import sys
import types
import os
import shlex
import inspect
import logging
__options = dict()

logger=logging.getLogger(__name__)

class opex(Exception):
	pass


def option(funcOrName):
	def check(func):
		for k, param in inspect.signature(func).parameters.items():
			if (param.kind == inspect.Parameter.VAR_KEYWORD or
			    param.kind == inspect.Parameter.KEYWORD_ONLY):
				raise SyntaxError(
				  "keyword arguments are not supported for config options")

	if isinstance(funcOrName, types.FunctionType):
		check(funcOrName)
		global __options
		__options[funcOrName.__name__] = funcOrName
		return funcOrName

	def wrapper(func):
		check(func)
		global __options
		__options[funcOrName] = func
		return func

	return wrapper


def enumerateConfigDir(configDir):
	fn_configDir = os.path.join(
	  os.path.expandvars(os.path.expanduser(os.getenv("XDG_CONFIG_HOME", "~"))),
	  configDir)

	if not os.path.exists(fn_configDir): return

	fn_configDir = os.path.realpath(fn_configDir)
	if not os.path.exists(fn_configDir): return

	if not os.path.isdir(fn_configDir): return

	for fb in os.listdir(fn_configDir):
		fe = os.path.splitext(fb)[1]
		if fe == ".cfg":
			yield os.path.join(fn_configDir, fb)


def findWorkdirFile(fb, ascend=False) -> (str, str):
	fn_base = os.getcwd()

	for _ in range(512):
		fn_cfg = os.path.join(fn_base, fb)
		logger.debug(f"looking for workdir file {fb} in {fn_cfg}")
		if os.path.exists(fn_cfg):
			return fn_base, fn_cfg
		if not ascend:
			return os.getcwd(), None
		fn_base1 = os.path.dirname(fn_base)
		if fn_base1 == fn_base:
			return os.getcwd(), None
		fn_base = fn_base1

	raise RuntimeError("failed to ascend workdir")


def loadOptions(*filenames,
                workdirFile=None,
                ascendWorkdir=False,
                configDir=None):

	filenames_actual = list(filenames)

	if configDir is not None:
		filenames_actual += list(*enumerateConfigDir(configDir))

	if workdirFile is not None:
		logger.debug(f"using workdir file {workdirFile} (ascend: {ascendWorkdir})")
		_, fn = findWorkdirFile(workdirFile, ascendWorkdir)
		if fn is not None:
			filenames_actual.append(fn)
	try:
		global __options
		for fn in filenames_actual:
			logger.info(f"processing config {fn}")
			if not os.path.exists(fn): continue
			with open(fn, "r") as f:
				lidx = 0

				def emit_error(msg):
					raise opex(f"config {fn}:{lidx}: {msg}")

				for ln in f:
					lidx += 1
					args = shlex.split(ln, comments=True)

					if len(args) < 1: continue

					cmd_name = args[0]
					args = args[1:]

					if cmd_name not in __options:
						emit_error(f"unknown command '{cmd_name}'")

					cmd = __options[cmd_name]
					params = inspect.signature(cmd).parameters

					binding = list()

					for k, param in params.items():
						if (param.kind == inspect.Parameter.POSITIONAL_ONLY or
						    param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD):
							if len(args) < 1:
								if param.default == inspect.Parameter.empty:
									emit_error(f"missing {k} argument for {cmd_name}")
								binding.append(param.default)
							else:
								if param.annotation != inspect.Parameter.empty:
									try:
										binding.append(param.annotation(args[0]))
									except ValueError as e:
										emit_error(f"invalid {k} argument for {cmd_name}: {e}")
								else:
									binding.append(args[0])
								args = args[1:]
						elif param.kind == inspect.Parameter.VAR_POSITIONAL:
							if param.annotation != inspect.Parameter.empty:
								try:
									for arg in args:
										binding.append(param.annotation(arg))
								except ValueError as e:
									emit_error(f"invalid {k} argument for {cmd_name}: {e}")
							else:
								binding += args
							args = list()
						else:
							raise RuntimeError("unexpected parameter kind")
					
					if len(args)>0:
						emit_error(f"too many arguments for {cmd_name}: expected {len(params)}, got {len(params)+len(args)}")
					
					cmd(*binding)
	except opex as e:
		logger.error(str(e))
		sys.exit(1)
