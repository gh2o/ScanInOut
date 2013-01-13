from .commands_base import (FieldedObject, StringField,
	DictField, BoolField, Field, CommandError)

class RPCRequest (FieldedObject):
	command = StringField ()
	fields = DictField ()

class RPCResponse (FieldedObject):
	success = BoolField ()
	fields = DictField (
		keyfield=StringField (),
		valfield=Field (required=False),
		required=False
	)
	error = CommandError.Field (required=False)
