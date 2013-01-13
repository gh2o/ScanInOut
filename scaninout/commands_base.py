import re
from collections import OrderedDict
import copy
import datetime

class ValidationError (ValueError):
	pass

class Field (object):

	actual_type = object
	base_type = object

	name = "<unknown>"
	__count = 0

	def __init__ (self, required=True, default=None):

		self.required = required
		self.__default = default

		self.order = Field.__count
		Field.__count += 1
	
	def clone_default (self):
		return copy.deepcopy (self.__default)

	def actual_to_base_impl (self, x):
		return x

	def base_to_actual_impl (self, x):
		return x

	def actual_to_base (self, x):
		self.validate (x)
		if x is not None:
			x = self.actual_to_base_impl (x)
			if not isinstance (x, self.base_type):
				raise TypeError ("actual_to_base_impl must return of type %r" % self.base_type)
		return x

	def base_to_actual (self, x):
		if x is not None:
			if not isinstance (x, self.base_type):
				raise TypeError ("input to base_to_actual_impl must be of type %r" % self.base_type)
			x = self.base_to_actual_impl (x)
		self.validate (x)
		return x

	def validate_impl (self, x):
		pass

	def validate (self, x):
		if x is None:
			if self.required:
				raise ValidationError ("field %r cannot be empty or None" % self.name)
		else:
			if not isinstance (x, self.actual_type):
				raise ValidationError ("field %r should be of type %r, not %r" %
					(self.name, self.actual_type, type (x)))
			self.validate_impl (x)

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
	def __init__ (self, emptyable=True, *args, **kwargs):
		Field.__init__ (self, *args, **kwargs)
		self.emptyable = emptyable
	def validate_impl (self, value):
		Field.validate_impl (self, value)
		if not self.emptyable and not value:
			raise ValidationError ("non-empty string required")

class DateTimeField (Field):
	FORMAT = '%Y-%m-%dT%H:%M:%SZ'
	actual_type = datetime.datetime
	base_type = basestring
	def actual_to_base_impl (self, x):
		return x.strftime (self.FORMAT)
	def base_to_actual_impl (self, x):
		return datetime.datetime.strptime (x, self.FORMAT)

for f in [BoolField, IntField, FloatField, StringField, DateTimeField]:
	Field.default_fields[f.actual_type] = f ()
	del f

class ListField (Field):
	actual_type = list
	base_type = list
	def __init__ (self, subfield=Field(), **kwargs):
		Field.__init__ (self, **kwargs)
		self.subfield = Field.to_field (subfield)
	def actual_to_base_impl (self, x):
		return [self.subfield.actual_to_base (q) for q in x]
	def base_to_actual_impl (self, x):
		return [self.subfield.base_to_actual (q) for q in x]
	def validate_impl (self, x):
		Field.validate_impl (self, x)
		[self.subfield.validate (q) for q in x]

class DictField (Field):
	actual_type = dict
	base_type = dict
	def __init__ (self, keyfield=StringField(), valfield=Field(), **kwargs):
		Field.__init__ (self, **kwargs)
		self.keyfield = Field.to_field (keyfield)
		self.valfield = Field.to_field (valfield)
	def actual_to_base_impl (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.actual_to_base (q) for q in keys]
		vals = [self.valfield.actual_to_base (q) for q in vals]
		return dict (zip (keys, vals))
	def base_to_actual_impl (self, x):
		if not x:
			return {}
		keys, vals = zip (*(x.iteritems ()))
		keys = [self.keyfield.base_to_actual (q) for q in keys]
		vals = [self.valfield.base_to_actual (q) for q in vals]
		return dict (zip (keys, vals))
	def validate_impl (self, x):
		Field.validate_impl (self, x)
		[self.keyfield.validate (q) for q in x.iterkeys ()]
		[self.valfield.validate (q) for q in x.itervalues ()]

for f in [ListField, DictField]:
	Field.default_fields[f.actual_type] = f ()
	del f

class FieldedObjectField (Field):

	# actual_type must be set
	actual_type = None
	base_type = dict

	def actual_to_base_impl (self, x):
		ret = {}
		for name, field in self.actual_type._fields.iteritems ():
			ret[name] = field.actual_to_base (getattr (x, name))
		return ret

	def base_to_actual_impl (self, x):
		kwargs = {}
		for name, field in self.actual_type._fields.iteritems ():
			value = field.base_to_actual (x.get (name, field.clone_default ()))
			kwargs[name] = value
		return self.actual_type (**kwargs)

	def validate_impl (self, x):
		Field.validate_impl (self, x)
		for name, field in self.actual_type._fields.iteritems ():
			field.validate (getattr (x, name))

class FieldedObjectMeta (type):

	def __init__ (self, name, bases, attrs):

		# check for conflicting names
		if attrs.get ("__metaclass__") is not type (self):
			for key in attrs.iterkeys ():
				if key.startswith ("__") and key.endswith ("__"):
					continue
				if key in FieldedObject.__dict__:
					raise TypeError ("conflicting attribute: %s" % key)

		fields_keys = self._fields_keys = []
		fields = self._fields = {}

		for key, val in attrs.items ():
			if isinstance (val, Field):
				if key.startswith ("_"):
					raise "field with underscore found (%s)!" % key
				val.name = key
				fields[key] = val
				delattr (self, key)

		fields_keys[:] = fields.keys ()
		fields_keys.sort (key=lambda k: fields[k].order)

		self.Field = type (name + "Field", (FieldedObjectField,), {"actual_type": self})
		self._field_instance = self.Field ()

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

		object.__setattr__ (self, x, val)
	
	def encode_to_base (self):
		return self._field_instance.actual_to_base (self)

	@classmethod
	def decode_from_base (cls, x):
		return cls._field_instance.base_to_actual (x)

	def validate_object (self):
		self._field_instance.validate (self)

class CommandError (FieldedObject, RuntimeError):

	id = StringField ()
	message = StringField ()

	def __init__ (self, id, message):
		FieldedObject.__init__ (self, id=id, message=message)
		Exception.__init__ (self, message)

	def __str__ (self):
		return "%s [%s]" % (self.message, self.id)

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
		return self.request_field.base_to_actual (x)

	def encode_request (self, x):
		return self.request_field.actual_to_base (x)

	def decode_response (self, x):
		return self.response_field.base_to_actual (x)

	def encode_response (self, x):
		return self.response_field.actual_to_base (x)

class Command (object):

	__metaclass__ = CommandMeta
