
__checks = list()
__help_printers = list()


def check(func):
	global __checks
	__checks.append(func)
	return func


def help_printer(func):
	global __help_printers
	__help_printers.append(func)
	return func


def runChecks():
  global __checks
  for check in __checks:
    check()

def help_printers():
	global __help_printers
	yield from __help_printers