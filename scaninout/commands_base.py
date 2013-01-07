class CommandMeta (type):
	def __new__ (cls, name, bases, attrs):
		if attrs.get ('__metaclass__') is cls:
			return type.__new__ (cls, name, bases, attrs)
		return type.__new__ (cls, name, bases, attrs)

class Command (object):
	__metaclass__ = CommandMeta

class Field (object):

	python_type = object
	json_type = object

	def python_to_json (self, x):
		return x

	def json_to_python (self, x):
		return x

	def python_to_json_validate (self, x):
		if not isinstance (x, self.python_type):
			raise TypeError ("arg to python_to_json must be of type %r" % self.python_type)
		ret = self.python_to_json (x)
		if not isinstance (ret, self.json_type):
			raise TypeError ("python_to_json must return of type %r" % self.json_type)
		return ret

	def json_to_python_validate (self, x):
		if not isinstance (x, self.json_type):
			raise TypeError ("input to json_to_python must be of type %r" % self.json_type)
		ret = self.json_to_python (x)
		if not isinstance (ret, self.python_type):
			raise TypeError ("json_to_python must return of type %r" % self.python_type)
		return ret

	default_fields = {}
	@classmethod
	def to_field (cls, f):
		return cls.default_fields.get (f, f)

class BoolField (Field):
	python_type = bool
	json_type = bool

class IntField (Field):
	python_type = int
	json_type = int

class FloatField (Field):
	python_type = float
	json_type = float

class StringField (Field):
	python_type = str
	json_type = str

for f in [BoolField, IntField, FloatField, StringField]:
	Field.default_fields[f.python_type] = f ()
	del f

class ListField (Field):
	python_type = list
	json_type = list
	def __init__ (self, subfield=None):
		self.subfield = Field.to_field (subfield)
	def python_to_json (self, x):
		return [self.subfield.python_to_json_validate (q) for q in x]
	def json_to_python (self, x):
		return [self.subfield.json_to_python_validate (q) for q in x]

class DictField (Field):
	python_type = dict
	json_type = dict
	def __init__ (self, keyfield=str, valfield=None):
		self.keyfield = Field.to_field (keyfield)
		self.valfield = Field.to_field (valfield)
	def python_to_json (self, x):
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.python_to_json_validate (q) for q in keys]
		vals = [self.valfield.python_to_json_validate (q) for q in vals]
		return dict (zip (key, vals))
	def json_to_python (self, x):
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.json_to_python_validate (q) for q in keys]
		vals = [self.valfield.json_to_python_validate (q) for q in vals]
		return dict (zip (key, vals))

for f in [ListField, DictField]:
	Field.default_fields[f.python_type] = f ()
	del f
