from .commands_base import (
	Command, Field, ListField, DictField,
	StringField, BoolField, IntField, FloatField
)
from .types import MemberInfoField, Member, Shift

class Ping (Command):
	pass

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
	class Response:
		members = ListField (Member.Field ())

class MemberScanInOut (Command):
	class Request:
		tag = StringField ()
	class Response:
		elapsed_hours = FloatField (required=False)
		scanned_in = BoolField ()

class MemberGetShifts (Command):
	class Request:
		id = int
	class Response:
		hours = float
		shifts = ListField (Shift.Field ())

########################################
# ENUMERATE COMMANDS                   #
########################################
commands = dict (
	(name, cls) for name, cls in globals ().iteritems ()
		if isinstance (cls, type) and issubclass (cls, Command) and cls is not Command
)
