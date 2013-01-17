import os
import datetime
import binascii
from ..commands_base import CommandError
from .. import commands
from ..types import Member, Shift
from . import db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import subqueryload

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
# GENERAL                              #
########################################

@public
@handles (commands.Ping)
def handle_Ping (request, session, conn):
	return request.response_class ()

@handles (commands.AuthenticatedPing)
def handle_AuthenticatedPing (request, session, conn):
	return request.response_class ()

@public
@handles (commands.GenerateNonce)
def handle_GenerateNonce (request, session, conn):
	conn.nonce = os.urandom (32)
	conn.signature = None
	return request.response_class (
		nonce_hex = binascii.hexlify (conn.nonce)
	)

@public
@handles (commands.PreloadSignature)
def handle_PreloadSignature (request, session, conn):
	try:
		conn.signature = binascii.unhexlify (request.signature_hex)
	except TypeError:
		raise CommandError ('invalid-signature', "Invalid hexadecimal signature.")
	return request.response_class ()

########################################
# MEMBERS                              #
########################################

@public
@handles (commands.MemberAdd)
def handle_MemberAdd (request, session, conn):
	member = request.member
	member.id = None
	session.add (member)
	return request.response_class (member=member)

@handles (commands.MemberEdit)
def handle_MemberEdit (request, session, conn):
	member = request.member
	if member.id is None:
		raise CommandError ("member-no-id", "id must be defined")
	session.merge (member)
	return request.response_class (member=member)

@handles (commands.MemberDelete)
def handle_MemberDelete (request, session, conn):
	obj = session.query (Member).get (request.id)
	if obj is None:
		raise CommandError ("member-not-found", "Member not found.")
	session.delete (obj)
	return request.response_class ()

@handles (commands.MemberGet)
def handle_MemberGet (request, session, conn):
	member = session.query (Member).get (request.id)
	if member is None:
		raise CommandError ("member-not-found", "Member not found.")
	return request.response_class (
		member = member,
	)

@handles (commands.MemberGetAll)
def handle_MemberGetAll (request, session, conn):

	query = session.query (Member)
	if request.with_shifts:
		query = query.options (subqueryload ('shifts'))

	members = query.all ()
	return request.response_class (
		members = members,
		shifts_lists = [m.shifts for m in members] if request.with_shifts else None
	)

@public
@handles (commands.MemberScanInOut)
def handle_MemberScanInOut (request, session, conn):

	member = session.query (Member).filter (Member.tag == request.tag).first ()
	if member is None:
		raise CommandError ("member-not-found", "Member not found.")

	elapsed_hours = None
	total_hours = None

	current_shift = (
		member.shifts_dynamic
			.filter (Shift.active == True)
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
		session.expire (member)
		elapsed_hours = current_shift.hours
		total_hours = member.hours
	
	return request.response_class (
		member = member,
		scanned_in = (current_shift is None),
		elapsed_hours = elapsed_hours,
		total_hours = total_hours,
	)

@handles (commands.MemberGetShifts)
def handle_MemberGetShifts (request, session, conn):

	member = session.query (Member).get (request.id)
	if not member:
		raise CommandError ("member-not-found", "Member not found.")

	return request.response_class (
		hours = member.hours,
		shifts = member.shifts
	)

@public
@handles (commands.MemberCheckTag)
def handle_MemberCheckTag (request, session, conn):
	cnt = session.query (Member).filter (Member.tag == request.tag).count ()
	return request.response_class (
		exists = (cnt > 0)
	)

@public
@handles (commands.MemberGetSignedIn)
def handle_MemberGetSignedIn (request, session, conn):
	pairs = session.query (Member, Shift).join (Shift).filter (Shift.active == True).all()
	return request.response_class (
		member_shift_pairs = pairs
	)

########################################
# ENUMERATE HANDLERS                   #
########################################
handlers = dict ((func.cmdclass, func) for func in globals ().itervalues ()
	if callable (func) and getattr (func, "handles", False))
