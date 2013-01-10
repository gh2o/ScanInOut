from collections import OrderedDict
import copy
import datetime

class Field (object):

	python_type = object
	json_type = object

	__count = 0

	def __init__ (self, required=True, default=None):
		self.required = required
		self.__default = default
		self.order = Field.__count
		Field.__count += 1
	
	def clone_default (self):
		return copy.deepcopy (self.__default)

	def python_to_json (self, x):
		return x

	def json_to_python (self, x):
		return x

	def python_to_json_validate (self, x):
		if x is not None:
			if not isinstance (x, self.python_type):
				raise TypeError ("arg to python_to_json must be of type %r" % self.python_type)
			x = self.python_to_json (x)
			if not isinstance (x, self.json_type):
				raise TypeError ("python_to_json must return of type %r" % self.json_type)
		return x

	def json_to_python_validate (self, x):
		if x is not None:
			if not isinstance (x, self.json_type):
				raise TypeError ("input to json_to_python must be of type %r" % self.json_type)
			x = self.json_to_python (x)
			if not isinstance (x, self.python_type):
				raise TypeError ("json_to_python must return of type %r" % self.python_type)
		return x

	default_fields = {}
	@classmethod
	def to_field (cls, f):
		if f is str or f is unicode:
			f = basestring
		return cls.default_fields.get (f, f)

	@staticmethod
	def filter_fields (obj):
		ret = {}
		if obj is not None:
			if not isinstance (obj, dict):
				obj = obj.__dict__
			for name, field in obj.iteritems ():
				field = Field.to_field (field)
				if isinstance (field, Field):
					ret[name] = field
		return ret

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
	python_type = basestring
	json_type = basestring

class DateTimeField (Field):
	FORMAT = '%Y-%m-%dT%H:%M:%SZ'
	python_type = datetime.datetime
	json_type = basestring
	def python_to_json (self, x):
		return x.strftime (self.FORMAT)
	def json_to_python (self, x):
		return datetime.datetime.strptime (x, self.FORMAT)

for f in [BoolField, IntField, FloatField, StringField, DateTimeField]:
	Field.default_fields[f.python_type] = f ()
	del f

class ListField (Field):
	python_type = list
	json_type = list
	def __init__ (self, subfield=None, **kwargs):
		Field.__init__ (self, **kwargs)
		self.subfield = Field.to_field (subfield)
	def python_to_json (self, x):
		return [self.subfield.python_to_json_validate (q) for q in x]
	def json_to_python (self, x):
		return [self.subfield.json_to_python_validate (q) for q in x]

class DictField (Field):
	python_type = dict
	json_type = dict
	def __init__ (self, keyfield=basestring, valfield=None, **kwargs):
		Field.__init__ (self, **kwargs)
		self.keyfield = Field.to_field (keyfield)
		self.valfield = Field.to_field (valfield)
	def python_to_json (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.python_to_json_validate (q) for q in keys]
		vals = [self.valfield.python_to_json_validate (q) for q in vals]
		return dict (zip (key, vals))
	def json_to_python (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.json_to_python_validate (q) for q in keys]
		vals = [self.valfield.json_to_python_validate (q) for q in vals]
		return dict (zip (key, vals))

for f in [ListField, DictField]:
	Field.default_fields[f.python_type] = f ()
	del f

class FieldContainer (object):

	__slots__ = ["__fielddict", "__data"]

	def __init__ (self, fielddict):
		self.__data = {}
		self.__fielddict = fielddict
		for name, field in fielddict.iteritems ():
			self.__data[name] = field.clone_default ()
	
	def __getattr__ (self, key):

		if key.startswith ("_FieldContainer__"):
			return object.__getattr__ (self, key)

		return self.__data[key]

	def __setattr__ (self, key, val):

		if key.startswith ("_FieldContainer__"):
			object.__setattr__ (self, key, val)
			return

		if key not in self.__fielddict:
			raise AttributeError ("Key %r not valid in field dictionary." % key)
		field = self.__fielddict[key]
		if val is not None and not isinstance (val, field.python_type):
			raise ValueError ("Value for %r is not of type %r." % (key, field.python_type))

		self.__data[key] = val

class FieldedObjectField (Field):

	# python_type must be set
	python_type = None
	json_type = dict

	def python_to_json (self, x):
		ret = {}
		for name, field in self.python_type._fields.iteritems ():
			ret[name] = field.python_to_json_validate (getattr (x, name))
		return ret

	def json_to_python (self, x):
		kwargs = {}
		for name, field in self.python_type._fields.iteritems ():
			value = field.json_to_python_validate (x.get (name, field.clone_default ()))
			if field.required and value is None:
				raise KeyError ("Required field %r not found." % name)
			kwargs[name] = value
		return self.python_type (**kwargs)

class FieldedObjectMeta (type):

	def __new__ (cls, name, bases, attrs):

		fields_keys = attrs["_fields_keys"] = []
		fields = attrs["_fields"] = {}

		for key, val in attrs.items ():
			if isinstance (val, Field):
				fields[key] = val
				del attrs[key]

		fields_keys[:] = fields.keys ()
		fields_keys.sort (key=lambda k: fields[k].order)

		ret = type.__new__ (cls, name, bases, attrs)
		ret.Field = type (name + "Field", (FieldedObjectField,), {"python_type": ret})
		return ret
	
class FieldedObject (object):

	__metaclass__ = FieldedObjectMeta

	def __init__ (self, **kwargs):

		for name, field in self._fields.iteritems ():
			setattr (self, name, kwargs.pop (name, field.clone_default ()))
		if kwargs:
			raise TypeError ("unknown arguments: %r" % kwargs.keys ())

	def __setattr__ (self, x, val):

		if x.startswith ("_sa_"):
			return object.__setattr__ (self, x, val)

		field = self._fields.get (x)
		if field is None:
			raise AttributeError

		if field.required and val is None:
			raise TypeError ("attribute %r for object %r cannot be None" % (x, self))
		if val is not None and not isinstance (val, field.python_type):
			raise TypeError ("attribute %r must be of type %r, not %r" % (x, field.python_type, type (val)))

		object.__setattr__ (self, x, val)

class CommandError (Exception):
	def __init__ (self, message):
		Exception.__init__ (self, message)
		self.message = message

class CommandContainer (object):

	__slots__ = ["__fields"]
	_cc_command = None
	_cc_class = None
	_cc_field = None

	def __init__ (self, **kwargs):
		self.__fields = self._cc_class (**kwargs)
	
	@property
	def fields (self):
		return self.__fields

	def create_request (self, **kwargs):
		return self._cc_command.Request (**kwargs)

	def create_response (self, **kwargs):
		return self._cc_command.Response (**kwargs)

	@classmethod
	def decode_from_json (cls, obj):

		class Dummy (CommandContainer):
			def __init__ (self, *args, **kwargs):
				pass

		ret = Dummy ()
		ret.__class__ = cls
		ret.__fields = cls._cc_field.json_to_python_validate (obj)
		return ret

	def encode_to_json (self):
		return self._cc_field.python_to_json_validate (self.__fields)

class CommandMeta (type):

	def __new__ (cls, name, bases, attrs):
		ret = type.__new__ (cls, name, bases, attrs)
		ret.__build_command_container ("Request")
		ret.__build_command_container ("Response")
		return ret

	def __build_command_container (self, rr):
		fields = Field.filter_fields (getattr (self, rr, None))
		klass = type (self.__name__ + rr + "Object", (FieldedObject,), fields)
		container = type (self.__name__ + rr + "CommandContainer", (CommandContainer,), {
			"_cc_command": self,
			"_cc_class": klass,
			"_cc_field": klass.Field (),
		})
		setattr (self, rr, container)

class Command (object):
	__metaclass__ = CommandMeta

