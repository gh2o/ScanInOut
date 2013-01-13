from .commands_base import (FieldedObject, IntField, StringField,
	DateTimeField, DictField, ValidationError)
from . import settings

class TagField (StringField):
	def __init__ (self):
		StringField.__init__ (self, emptyable=False)
	def validate_impl (self, value):
		StringField.validate_impl (self, value)
		if not settings.validate_tag (value):
			raise ValidationError ("invalid tag")

class MemberInfoField (FieldedObject):

	id = IntField (required=False)
	name = StringField ()

class Member (FieldedObject):

	id = IntField (required=False)
	tag = TagField ()

	first_name = StringField (emptyable=False)
	last_name = StringField (emptyable=False)

	info = DictField (default={})

	@property
	def name (self):
		return "%s %s" % (self.first_name, self.last_name)

class Shift (FieldedObject):

	id = IntField (required=False)

	member_id = IntField ()
	start_time = DateTimeField ()
	end_time = DateTimeField (required=False)
