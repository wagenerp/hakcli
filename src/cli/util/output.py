import sys

def werror(v: str):
	sys.stderr.write(f"\x1b[31;1mError\x1b[30;0m: {v}\n")


def wwarn(v: str):
	sys.stderr.write(f"\x1b[33;1mWarning\x1b[30;0m: {v}\n")

