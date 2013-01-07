from .commands_base import Command, Field, ListField, DictField
from .types import MemberInfoField, Member

########################################
# MEMBER INFO FIELDS                   #
########################################

class MemberInfoFieldField (Field):
	python_type = MemberInfoField
	json_type = dict

class MemberInfoFieldAdd (Command):
	class Request:
		field = MemberInfoFieldField ()
	class Response:
		field = MemberInfoFieldField ()

class MemberInfoFieldEdit (Command):
	class Request:
		field = MemberInfoFieldField ()
	class Response:
		field = MemberInfoFieldField ()

class MemberInfoFieldDelete (Command):
	class Request:
		id = int

class MemberInfoFieldGet (Command):
	class Request:
		id = int
	class Response:
		field = MemberInfoFieldField ()

class MemberInfoFieldGetAll (Command):
	class Response:
		fields = ListField (MemberInfoFieldField ())

########################################
# MEMBER                               #
########################################

class MemberField (Field):
	python_type = Member
	json_type = dict

class MemberAdd (Command):
	class Request:
		member = MemberField ()
	class Response:
		member = MemberField ()

class MemberEdit (Command):
	class Request:
		member = MemberField ()
	class Response:
		member = MemberField ()

class MemberDelete (Command):
	class Request:
		id = int

class MemberGet (Command):
	class Request:
		id = int
	class Response:
		member = MemberField ()

class MemberGetAll (Command):
	class Response:
		members = ListField (MemberField ())
