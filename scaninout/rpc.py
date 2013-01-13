from .commands_base import (FieldedObject, StringField,
	DictField, BoolField, CommandError)

class RPCRequest (FieldedObject):
	command = StringField ()
	fields = DictField ()

class RPCResponse (FieldedObject):
	success = BoolField ()
	fields = DictField (required=False)
	error = CommandError.Field (required=False)
