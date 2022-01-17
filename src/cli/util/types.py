import os
import re

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

def Regex(s: str):
	"""Regular expression and flags in the form <delimiter>regex<delimiter>flags"""

	if len(s) < 2: raise ValueError(f"invalid regex literal: '{s}'")
	delim = s[0]
	items = s[1:].split(s[0])

	pattern = delim.join(items[:-1])
	flags = 0
	for sym in items[-1]: # a i l s x
		syml = sym.lower()
		if syml == "a": flags += re.A
		elif syml == "i": flags += re.I
		elif syml == "l": flags += re.L
		elif syml == "s": flags += re.S
		elif syml == "x": flags += re.X
		else: raise ValueError(f"invalid regex flag char: {sym}")

	return re.compile(pattern,flags)

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
