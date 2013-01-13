import json
import datetime

from sqlalchemy import (
	MetaData, Table, Column,
	ForeignKey, Float, Integer, String, DateTime, LargeBinary,
	TypeDecorator,
	extract, cast, case, func,
	event
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import mapper, relationship, column_property, Query

from .. import settings
from ..types import MemberInfoField, Member, Shift

metadata = MetaData ()

class JSON (TypeDecorator):
	impl = String
	def process_bind_param (self, value, dialect):
		return json.dumps (value) if value is not None else None
	def process_result_value (self, value, dialect):
		return json.loads (value) if value is not None else None

def build_table (tbname, focls, column_args={}, column_kwargs={}, **kwargs):

	columns = []

	column_args = column_args.copy ()
	column_kwargs = column_kwargs.copy ()

	for name in focls._fields_keys:

		field = focls._fields[name]
		ptype = field.actual_type

		cargs = column_args.pop (name, [])
		ckwargs = column_kwargs.pop (name, {})

		ckwargs.setdefault ("default", field.clone_default ())
		ckwargs.setdefault ("nullable", not field.required)

		ctype = None

		if ptype is int:
			ctype = Integer
			ckwargs["primary_key"] = (name == 'id')
		elif ptype is basestring:
			ctype = String
		elif ptype is list or ptype is dict:
			ctype = JSON
		elif ptype is datetime.datetime:
			ctype = DateTime
		else:
			raise TypeError ("unknown actual_type %r" % ptype)

		columns.append (Column (name, ctype, *cargs, **ckwargs))
	
	if column_args:
		raise ValueError ("unknown column_args keys: %r" % column_args.keys ())
	if column_kwargs:
		raise ValueError ("unknown column_kwargs keys: %r" % column_args.keys ())

	table = Table (tbname, metadata, *columns)
	table.mapper = mapper (focls, table, **kwargs)
	return table

member_info_fields = build_table ("member_info_fields", MemberInfoField,
	column_kwargs={
		"name": {"unique": True, "index": True},
	},
)

members = build_table ("members", Member,
	column_kwargs={
		"tag": {"unique": True, "index": True},
	},
	properties={
		"shifts": relationship (Shift, backref="member", lazy="select")
	},
)

shifts = build_table ("shifts", Shift,
	column_args={
		"member_id": [ForeignKey (Member.id)],
	},
	column_kwargs={
		"member_id": {"index": True},
		"start_time": {"index": True},
		"end_time": {"index": True},
	},
)

def utc_timestamp_to_local_timestamp (ts):
	return func.datetime (ts, 'localtime')

def local_timestamp_to_utc_timestamp (ts):
	return func.datetime (ts, 'utc')

def utc_timestamp_to_epoch (ts):
	return extract ('epoch', ts)

def epoch_to_utc_timestamp (ts):
	return func.datetime (ts, 'unixepoch')

def local_timestamp_to_epoch (ts):
	return extract ('epoch', local_timestamp_to_utc_timestamp (ts))

def epoch_to_local_timestamp (ts):
	return func.datetime (ts, 'unixepoch', 'localtime')

cutoff_offset = settings.expires_cutoff_time * 3600

shifts.mapper.add_properties ({
	"hours": column_property (
		cast (case (
			whens=[(Shift.end_time == None, 0.0)],
			else_=(
				utc_timestamp_to_epoch (Shift.end_time) -
				utc_timestamp_to_epoch (Shift.start_time)
			) / 3600.
		), Float ())
	),
	"expired": column_property (
		(Shift.end_time == None) &
		(
			func.date (epoch_to_local_timestamp (utc_timestamp_to_epoch (func.now ()) - cutoff_offset)) !=
			func.date (epoch_to_local_timestamp (utc_timestamp_to_epoch (Shift.start_time) - cutoff_offset))
		)
	),
})

members.mapper.add_property ("hours", column_property (
	Query ([func.coalesce (func.sum (Shift.hours), 0.0)]).join (Member).label ("hours")
))

@event.listens_for (Engine, "connect")
def sqlite_enable_foreign_keys (conn, record):
	cursor = conn.cursor ()
	cursor.execute ("PRAGMA foreign_keys=ON")
	cursor.close ()
