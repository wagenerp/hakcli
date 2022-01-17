import re
import sys
import shutil
import textwrap
from collections import namedtuple, defaultdict

e_escape = re.compile(b"\x1b("
                      b"\\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]" # CSI sequence
                      b")")

def RemoveEscape(v):
	return	e_escape.sub(b"", v.encode()).decode()

class TablePrinter:
	cell_t = namedtuple("cell_t", "content width")

	def __init__(s, firstRowHeader=True, columnSeparator=" ", defaultOutput = sys.stdout):
		s._rows = list()
		s._nColumns = 0
		s._nRows = 0
		s._columnWidths = defaultdict(lambda: 0)
		s._dirty = False
		s._text = ""
		s._defaultOutput = defaultOutput

		s.firstRowHeader = firstRowHeader
		s.columnSeparator = columnSeparator
	
	def reset(s):
		s._nColumns = 0
		s._nRows = 0
		s._columnWidths = defaultdict(lambda: 0)
		s._dirty = False
		s._text = ""


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
			s._text += s.renderSeparator()

		for i in range(1, len(s._rows)):
			s._text += s.renderRow(i)
	
	def sort(s,key=None,escape = True,reverse=False):
		prefix=list()
		if s.firstRowHeader: 
			prefix=list(s._rows[0:1])
			s._rows=s._rows[1:]
		
		if key is None:
			key = lambda a:a
		
		key_unwrapped = key
		if escape:
			key = lambda a: key_unwrapped(tuple(RemoveEscape(v.content) for v in a))
		else:
			key = lambda a: key_unwrapped(tuple(v.content for v in a))
		
		s._rows= sorted(s._rows,key=key,reverse=reverse)

		if s.firstRowHeader:
			s._rows= prefix + s._rows


		i0 = 1 if s.firstRowHeader else 0
		


	@property
	def nColumns(s):
		return s._nColumns

	@property
	def nRows(s):
		return len(s._rows)

	def __str__(s):
		s.render()

		return s._text

	def __enter__(s):
		return s

	def __exit__(s, *args, **kwargs):
		s.render()
		s._defaultOutput.write(s._text)
		s.reset()




class WrappedPrinter:
	def __init__(s, f, indent):
		line_width = 80
		if f == sys.stdout or f == sys.stderr:
			line_width = shutil.get_terminal_size((line_width, 20)).columns

		indent_str = '  ' * indent

		s.wrapper = textwrap.TextWrapper(width=line_width,
		                                 tabsize=2,
		                                 initial_indent=indent_str,
		                                 subsequent_indent=indent_str)

		s.f = f
		s.indent = indent
		s.stack = list()
	
	def write(s,data):
		s.f.write(s.wrapper.fill(data) + "\n")


	def __enter__(s):
		s.stack.append("")
		return s

	def __exit__(s, *args, **kwargs):

		s.write( s.stack.pop())

	def __iadd__(s, v):
		s.stack[-1] += str(v)
		return s

	def __imul__(s,v):
		s.write(v)
		return s