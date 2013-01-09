import datetime
from ..commands_base import CommandError
from .. import commands
from ..types import Member
from . import db

def protected (func):
	func.protected = True
	return func

def handles (cmdclass):
	def inner (func):
		func.handles = True
		func.cmdclass = cmdclass
		return func
	return inner

########################################
# MEMBERS                              #
########################################

@handles (commands.MemberAdd)
def handle_MemberAdd (request, session):
	member = request.fields.member
	member.id = None
	session.add (member)
	session.commit ()
	return request.create_response (member=member)

@protected
@handles (commands.MemberEdit)
def handle_MemberEdit (request, session):
	member = request.fields.member
	if member.id is None:
		raise CommandError ("id must be defined")
	session.add (member)
	session.commit ()
	return request.create_response (member=member)

@protected
@handles (commands.MemberDelete)
def handle_MemberDelete (request, session):
	query = session.query (Member).filter (Member.id == request.fields.id)
	if query.count () == 0:
		raise CommandError ("Member not found.")
	query.delete ()
	session.commit ()
	return request.create_response ()

@protected
@handles (commands.MemberGet)
def handle_MemberGet (request, session):
	obj = session.query (Member).filter (Member.id == request.fields.id).first ()
	if obj is None:
		raise CommandError ("Member not found.")
	return request.create_response (member=obj)
	
@protected
@handles (commands.MemberGetAll)
def handle_MemberGetAll (request, session):
	return request.create_response (
		members = list (session.query (Member))
	)

########################################
# ENUMERATE HANDLERS                   #
########################################
handlers = dict ((func.cmdclass, func) for func in globals ().itervalues ()
	if callable (func) and getattr (func, "handles", False))
