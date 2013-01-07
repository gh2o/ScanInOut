from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base ()

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
