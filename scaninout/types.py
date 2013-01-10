from .commands_base import FieldedObject, IntField, StringField, DateTimeField, DictField

class MemberInfoField (FieldedObject):

	id = IntField (required=False)
	name = StringField ()

class Member (FieldedObject):

	id = IntField (required=False)
	tag = StringField ()

	first_name = StringField ()
	last_name = StringField ()

	info = DictField (default={})

class Shift (FieldedObject):

	id = IntField (required=False)

	member_id = IntField ()
	start_time = DateTimeField ()
	end_time = DateTimeField (required=False)
