__patterns=list()
def pattern(cls):
  global __patterns
  __patterns.append(cls)
  return cls

def patterns():
  global __patterns
  yield from __patterns

@pattern
class Flag:
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

		return Flag(s, short, long, description)



# @pattern
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


# @pattern
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


# @pattern
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


# @pattern
class ArgVariable:
  def __init__(s, owner, type, default, name, description=None, required=False):
    s._value = default
    s._default = default
    s._isset = False
    s._name = name

    @owner.argument(name=name)
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


# @pattern
class ArgListVariable:
  def __init__(s, owner, type, name, description=None, required=False):
    s._values = list()
    s._name = name
    s._type = type

    @owner.argument(name=name, repeated=True)
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