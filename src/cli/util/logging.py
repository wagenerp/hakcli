import logging
import datetime


def get_timezone_letter():
	offset = datetime.datetime.now() - datetime.datetime.utcnow()
	offset = int(round(offset.seconds + offset.microseconds * 1e-6))
	if (offset % 3600) != 0: return "J"
	offset = int(offset // 3600)
	if abs(offset) > 12: return "J"
	if offset >= 10:
		return chr(ord('K') + offset - 10)
	elif offset > 0:
		return chr(ord('A') + offset - 1)
	elif offset < 0:
		return chr(ord('N') - offset - 1)
	else:
		return 'Z'


class ALPFormatter(logging.Formatter):
	def __init__(s, logOrigin=False, logTime=True):
		logging.Formatter.__init__(s)
		s.logOrigin = logOrigin
		s.logTime = logTime

	def format(s, rec: logging.LogRecord):
		res = ""
		if False:
			pass
		elif rec.levelno >= logging.FATAL:
			res += "\x1b[38;2;255;60;60mFAT\x1b[30;0m "
		elif rec.levelno >= logging.ERROR:
			res += "\x1b[38;2;255;60;60mERR\x1b[30;0m "
		elif rec.levelno >= logging.WARNING:
			res += "\x1b[38;2;255;200;40mWRN\x1b[30;0m "
		elif rec.levelno >= logging.INFO:
			res += "\x1b[38;2;40;255;255mINF\x1b[30;0m "
		elif rec.levelno >= logging.DEBUG:
			res += "\x1b[38;2;255;40;255mDBG\x1b[30;0m "
		else:
			res += "\x1b[38;2;127;40;255mUNK\x1b[30;0m "
		
		if s.logTime:
			t=datetime.datetime.now()
			timestr=t.isoformat(sep=' ',timespec="milliseconds")
			res += f"\x1b[38;2;120;120;200m{timestr}{get_timezone_letter()} \x1b[30;0m"

		res += f"{rec.name} "

		if s.logOrigin:
			res += f"\x1b[38;2;120;120;200m{rec.pathname} {rec.lineno} \x1b[30;0m"

		msg = rec.msg
		if len(rec.args) > 0:
			msg = msg % rec.args

		res += msg
		return res
	
	def imbue(s,handler:logging.Handler):
		handler.setFormatter(s)
		return handler

def configureLogging(level=logging.INFO, handler = None):
	if handler is None:
		handler = logging.StreamHandler()
	logging.basicConfig(level=level,
											handlers=(ALPFormatter().imbue(
												handler), ))

