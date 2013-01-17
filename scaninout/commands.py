from .commands_base import (
	Command, Field, ListField, DictField, TupleField,
	StringField, BoolField, IntField, FloatField,
	DateTimeField
)
from .types import MemberInfoField, Member, Shift

class Ping (Command):
	pass

class AuthenticatedPing (Command):
	pass

class GenerateNonce (Command):
	class Response:
		nonce_hex = StringField ()

class PreloadSignature (Command):
	class Request:
		signature_hex = StringField ()

########################################
# MEMBER INFO FIELDS                   #
########################################

class MemberInfoFieldAdd (Command):
	class Request:
		field = MemberInfoField.Field ()
	class Response:
		field = MemberInfoField.Field ()

class MemberInfoFieldEdit (Command):
	class Request:
		field = MemberInfoField.Field ()
	class Response:
		field = MemberInfoField.Field ()

class MemberInfoFieldDelete (Command):
	class Request:
		id = int

class MemberInfoFieldGet (Command):
	class Request:
		id = int
	class Response:
		field = MemberInfoField.Field ()

class MemberInfoFieldGetAll (Command):
	class Response:
		fields = ListField (MemberInfoField.Field ())

########################################
# MEMBERS                              #
########################################

class MemberAdd (Command):
	class Request:
		member = Member.Field ()
	class Response:
		member = Member.Field ()

class MemberEdit (Command):
	class Request:
		member = Member.Field ()
	class Response:
		member = Member.Field ()

class MemberDelete (Command):
	class Request:
		id = int

class MemberGet (Command):
	class Request:
		id = int
	class Response:
		member = Member.Field ()

class MemberGetAll (Command):
	class Request:
		with_shifts = BoolField (default=False)
	class Response:
		members = ListField (Member.Field ())
		shifts_lists = ListField (ListField (Shift.Field ()), required=False)

class MemberScanInOut (Command):
	class Request:
		tag = StringField ()
	class Response:
		member = Member.Field ()
		scanned_in = BoolField ()
		elapsed_hours = FloatField (required=False)
		total_hours = FloatField (required=False)

class MemberGetShifts (Command):
	class Request:
		id = int
	class Response:
		hours = float
		shifts = ListField (Shift.Field ())

class MemberCheckTag (Command):
	class Request:
		tag = StringField ()
	class Response:
		exists = BoolField ()

class MemberGetSignedIn (Command):
	class Response:
		member_shift_pairs = ListField (TupleField (
			Member.Field (),
			Shift.Field ()
		))

########################################
# ENUMERATE COMMANDS                   #
########################################
commands = dict (
	(name, cls) for name, cls in globals ().iteritems ()
		if isinstance (cls, type) and issubclass (cls, Command) and cls is not Command
)
