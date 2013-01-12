import re
from collections import OrderedDict
import copy
import datetime

class Field (object):

	actual_type = object
	base_type = object

	__count = 0

	def __init__ (self, required=True, default=None):
		self.required = required
		self.__default = default
		self.order = Field.__count
		Field.__count += 1
	
	def clone_default (self):
		return copy.deepcopy (self.__default)

	def actual_to_base (self, x):
		return x

	def base_to_actual (self, x):
		return x

	def actual_to_base_validate (self, x):
		if x is not None:
			if not isinstance (x, self.actual_type):
				raise TypeError ("arg to actual_to_base must be of type %r" % self.actual_type)
			x = self.actual_to_base (x)
			if not isinstance (x, self.base_type):
				raise TypeError ("actual_to_base must return of type %r" % self.base_type)
		return x

	def base_to_actual_validate (self, x):
		if x is not None:
			if not isinstance (x, self.base_type):
				raise TypeError ("input to base_to_actual must be of type %r" % self.base_type)
			x = self.base_to_actual (x)
			if not isinstance (x, self.actual_type):
				raise TypeError ("base_to_actual must return of type %r" % self.actual_type)
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
	actual_type = bool
	base_type = bool

class IntField (Field):
	actual_type = int
	base_type = int

class FloatField (Field):
	actual_type = float
	base_type = float

class StringField (Field):
	actual_type = basestring
	base_type = basestring

class DateTimeField (Field):
	FORMAT = '%Y-%m-%dT%H:%M:%SZ'
	actual_type = datetime.datetime
	base_type = basestring
	def actual_to_base (self, x):
		return x.strftime (self.FORMAT)
	def base_to_actual (self, x):
		return datetime.datetime.strptime (x, self.FORMAT)

for f in [BoolField, IntField, FloatField, StringField, DateTimeField]:
	Field.default_fields[f.actual_type] = f ()
	del f

class ListField (Field):
	actual_type = list
	base_type = list
	def __init__ (self, subfield=None, **kwargs):
		Field.__init__ (self, **kwargs)
		self.subfield = Field.to_field (subfield)
	def actual_to_base (self, x):
		return [self.subfield.actual_to_base_validate (q) for q in x]
	def base_to_actual (self, x):
		return [self.subfield.base_to_actual_validate (q) for q in x]

class DictField (Field):
	actual_type = dict
	base_type = dict
	def __init__ (self, keyfield=basestring, valfield=None, **kwargs):
		Field.__init__ (self, **kwargs)
		self.keyfield = Field.to_field (keyfield)
		self.valfield = Field.to_field (valfield)
	def actual_to_base (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.actual_to_base_validate (q) for q in keys]
		vals = [self.valfield.actual_to_base_validate (q) for q in vals]
		return dict (zip (key, vals))
	def base_to_actual (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.base_to_actual_validate (q) for q in keys]
		vals = [self.valfield.base_to_actual_validate (q) for q in vals]
		return dict (zip (key, vals))

for f in [ListField, DictField]:
	Field.default_fields[f.actual_type] = f ()
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
		if val is not None and not isinstance (val, field.actual_type):
			raise ValueError ("Value for %r is not of type %r." % (key, field.actual_type))

		self.__data[key] = val

class FieldedObjectField (Field):

	# actual_type must be set
	actual_type = None
	base_type = dict

	def actual_to_base (self, x):
		ret = {}
		for name, field in self.actual_type._fields.iteritems ():
			ret[name] = field.actual_to_base_validate (getattr (x, name))
		return ret

	def base_to_actual (self, x):
		kwargs = {}
		for name, field in self.actual_type._fields.iteritems ():
			value = field.base_to_actual_validate (x.get (name, field.clone_default ()))
			if field.required and value is None:
				raise KeyError ("Required field %r not found." % name)
			kwargs[name] = value
		return self.actual_type (**kwargs)

class FieldedObjectMeta (type):

	def __init__ (self, name, bases, attrs):

		fields_keys = self._fields_keys = []
		fields = self._fields = {}

		for key, val in attrs.items ():
			if isinstance (val, Field):
				if key.startswith ("_"):
					raise "field with underscore found (%s)!" % key
				fields[key] = val
				delattr (self, key)

		fields_keys[:] = fields.keys ()
		fields_keys.sort (key=lambda k: fields[k].order)

		self.Field = type (name + "Field", (FieldedObjectField,), {"actual_type": self})

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
		if val is not None and not isinstance (val, field.actual_type):
			raise TypeError ("attribute %r must be of type %r, not %r" % (x, field.actual_type, type (val)))

		object.__setattr__ (self, x, val)
	
class CommandError (RuntimeError):
	def __init__ (self, message):
		Exception.__init__ (self, message)
		self.message = message

class CommandMeta (type):

	def __init__ (self, name, bases, attrs):

		type.__init__ (self, name, bases, attrs)

		self.__build_container ("Request", attrs)
		self.__build_container ("Response", attrs)
		self.Request.response_class = self.Response
		self.Response.request_class = self.Request
		self.request_field = self.Request.Field ()
		self.response_field = self.Response.Field ()

	def __build_container (self, rr, attrs):
		foattrs = Field.filter_fields (attrs.get (rr))
		klass = type (self.__name__ + rr, (FieldedObject,), foattrs)
		setattr (self, rr, klass)
	
	def __call__ (self, *args, **kwargs):
		raise TypeError ("cannot create %r instances" % self.__name__)

	def decode_request (self, x):
		return self.request_field.base_to_actual_validate (x)

	def encode_request (self, x):
		return self.request_field.actual_to_base_validate (x)

	def decode_response (self, x):
		return self.response_field.base_to_actual_validate (x)

	def encode_response (self, x):
		return self.response_field.actual_to_base_validate (x)

class Command (object):

	__metaclass__ = CommandMeta
