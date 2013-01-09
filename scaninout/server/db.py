import json
import datetime

from sqlalchemy import (
	MetaData, Table, Column,
	ForeignKey, Integer, String, DateTime, LargeBinary,
	TypeDecorator
)
from sqlalchemy.orm import mapper

from ..types import MemberInfoField, Member, Shift

metadata = MetaData ()

class JSON (TypeDecorator):
	impl = String
	def process_bind_param (self, value, dialect):
		return json.dumps (value) if value is not None else None
	def process_result_value (self, value, dialect):
		return json.loads (value) if value is not None else None

def build_table (tbname, focls, *mapper_args, **mapper_kwargs):
	columns = []
	for name in focls._fields_keys:
		field = focls._fields[name]
		ckwargs = {"nullable": not field.required}
		ctype = None
		ptype = field.python_type
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
			raise TypeError ("unknown python_type %r" % ptype)
		columns.append (Column (name, ctype, **ckwargs))
	table = Table (tbname, metadata, *columns)
	mapper (focls, table, *mapper_args, **mapper_kwargs)
	return table

member_info_fields = build_table ("member_info_fields", MemberInfoField)
members = build_table ("members", Member)
shifts = build_table ("shifts", Shift)

"""
class MemberInfoField (Base):

	__tablename__ = "member_info_fields"

	id = Column (Integer, primary_key=True)
	name = Column (String, nullable=False)

class Member (Base):

	__tablename__ = "members"

	id = Column (Integer, primary_key=True)
	tag = Column (String, nullable=False, unique=True, index=True)

	first_name = Column (String, nullable=False)
	last_name = Column (String, nullable=False)
	name = column_property (first_name + " " + last_name)

	scan_time = Column (DateTime)

	shifts = relationship ("Shift", backref="member")

class Shift (Base):

	__tablename__ = "shifts"

	id = Column (Integer, primary_key=True)
	member_id = Column (Integer, ForeignKey (Member.id), nullable=False, index=True)

	start_time = Column (DateTime, nullable=False)
	end_time = Column (DateTime, nullable=False)
"""
