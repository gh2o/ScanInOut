import datetime
from ..commands_base import CommandError
from .. import commands
from ..types import Member, Shift
from . import db

def public (func):
	func.public = True
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

@public
@handles (commands.MemberAdd)
def handle_MemberAdd (request, session):
	member = request.fields.member
	member.id = None
	session.add (member)
	return request.create_response (member=member)

@handles (commands.MemberEdit)
def handle_MemberEdit (request, session):
	member = request.fields.member
	if member.id is None:
		raise CommandError ("id must be defined")
	session.add (member)
	return request.create_response (member=member)

@handles (commands.MemberDelete)
def handle_MemberDelete (request, session):
	obj = session.query (Member).get (request.fields.id)
	if obj is None:
		raise CommandError ("Member not found.")
	session.delete (obj)
	return request.create_response ()

@handles (commands.MemberGet)
def handle_MemberGet (request, session):
	obj = session.query (Member).get (request.fields.id)
	if obj is None:
		raise CommandError ("Member not found.")
	return request.create_response (member=obj)
	
@handles (commands.MemberGetAll)
def handle_MemberGetAll (request, session):
	return request.create_response (
		members = list (session.query (Member))
	)

@public
@handles (commands.MemberScanInOut)
def handle_MemberScanInOut (request, session):

	member = session.query (Member).filter (Member.tag == request.fields.tag).first ()
	if member is None:
		raise CommandError ("Member not found.")

	elapsed_hours = None

	current_shift = (
		session.query (Shift)
			.join (Member)
			.filter (Shift.expired == False)
			.filter (Shift.end_time == None)
			.order_by (Shift.start_time.desc ())
			.first ()
	)

	if current_shift is None:
		session.add (Shift (
			member_id = member.id,
			start_time = datetime.datetime.utcnow (),
		))
	else:
		current_shift.end_time = datetime.datetime.utcnow ()
		session.add (current_shift)
		session.flush ()
		elapsed_hours = current_shift.hours
	
	return request.create_response (
		scanned_in = (current_shift is None),
		elapsed_hours = elapsed_hours,
	)

@handles (commands.MemberGetShifts)
def handle_MemberGetShifts (request, session):

	member = session.query (Member).get (request.fields.id)
	if not member:
		raise CommandError ("Member not found.")

	return request.create_response (
		hours = member.hours,
		shifts = member.shifts
	)

########################################
# ENUMERATE HANDLERS                   #
########################################
handlers = dict ((func.cmdclass, func) for func in globals ().itervalues ()
	if callable (func) and getattr (func, "handles", False))
