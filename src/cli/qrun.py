import sys

commands = dict()


def qruncmd(index=None):
	global commands
	if index is None:
		for i in range(1, 13):
			if i not in commands:
				index = i
				break

	def wrapper(func):
		global commands
		commands[index] = func
		return func

	return wrapper


def qrun():
	global commands
	for arg in sys.argv[1:]:
		if arg == "describe":
			for index in sorted(commands):
				print(index)
		else:
			try:
				index = int(arg)
			except ValueError:
				exit(1)
			if index not in commands:
				exit(1)
			commands[index]()
