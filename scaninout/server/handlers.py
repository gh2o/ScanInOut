import datetime
from ..commands_base import CommandError
from .. import commands
from ..types import Member, Shift
from . import db
from sqlalchemy.exc import IntegrityError

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
@handles (commands.Ping)
def handle_Ping (request, session):
	return request.response_class ()

@public
@handles (commands.MemberAdd)
def handle_MemberAdd (request, session):
	member = request.member
	member.id = None
	session.add (member)
	return request.response_class (member=member)

@handles (commands.MemberEdit)
def handle_MemberEdit (request, session):
	member = request.member
	if member.id is None:
		raise CommandError ("member-no-id", "id must be defined")
	session.add (member)
	return request.response_class (member=member)

@handles (commands.MemberDelete)
def handle_MemberDelete (request, session):
	obj = session.query (Member).get (request.id)
	if obj is None:
		raise CommandError ("member-not-found", "Member not found.")
	session.delete (obj)
	return request.response_class ()

@handles (commands.MemberGet)
def handle_MemberGet (request, session):
	obj = session.query (Member).get (request.id)
	if obj is None:
		raise CommandError ("member-not-found", "Member not found.")
	return request.response_class (member=obj)

@handles (commands.MemberGetAll)
def handle_MemberGetAll (request, session):
	return request.response_class (
		members = list (session.query (Member))
	)

@public
@handles (commands.MemberScanInOut)
def handle_MemberScanInOut (request, session):

	member = session.query (Member).filter (Member.tag == request.tag).first ()
	if member is None:
		raise CommandError ("member-not-found", "Member not found.")

	elapsed_hours = None
	total_hours = None

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
		total_hours = member.hours
	
	return request.response_class (
		member = member,
		scanned_in = (current_shift is None),
		elapsed_hours = elapsed_hours,
		total_hours = total_hours,
	)

@handles (commands.MemberGetShifts)
def handle_MemberGetShifts (request, session):

	member = session.query (Member).get (request.id)
	if not member:
		raise CommandError ("member-not-found", "Member not found.")

	return request.response_class (
		hours = member.hours,
		shifts = member.shifts
	)

@public
@handles (commands.MemberCheckTag)
def handle_MemberCheckTag (request, session):
	cnt = session.query (Member).filter (Member.tag == request.tag).count ()
	return request.response_class (
		exists = (cnt > 0)
	)

########################################
# ENUMERATE HANDLERS                   #
########################################
handlers = dict ((func.cmdclass, func) for func in globals ().itervalues ()
	if callable (func) and getattr (func, "handles", False))
