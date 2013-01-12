import json
import sqlalchemy
import sqlalchemy.orm

from ..commands_base import Command, CommandError
from ..commands import commands
from .handlers import handlers
from .db import metadata as db_metadata

class Server (object):

	def __init__ (self, dbpath):
		self.dbpath = dbpath
		self.db = sqlalchemy.create_engine ("sqlite:///" + dbpath, echo=True)
		self.create_session = sqlalchemy.orm.sessionmaker (bind=self.db)
		db_metadata.bind = self.db
		db_metadata.create_all ()

	def handle_connection (self, sock, addr):

		rfile = sock.makefile ('r', -1)
		wfile = sock.makefile ('w', 0)

		while True:

			raw = rfile.readline ()
			if not raw:
				break

			ret = {}
			ferr = CommandError ("Format error.")

			try:

				try:
					obj = json.loads (raw)
				except ValueError as e:
					raise CommandError ("JSON error: " + str (e))

				if not isinstance (obj, dict):
					raise ferr

				command = obj.get ("command")
				if not isinstance (command, basestring):
					raise ferr

				fields = obj.get ("fields")
				if not isinstance (fields, dict):
					raise ferr

				ret = {
					"success": True,
					"fields": self.handle_command (command, fields)
				}

			except CommandError as e:

				ret = {
					"success": False,
					"message": str (e)
				}

			except:

				ret = {
					"success": False,
					"message": "Critical error. See log for details."
				}

				import traceback
				traceback.print_exc ()

			wfile.write (json.dumps (ret) + '\n')
	
	def handle_command (self, cmdstring, fields):

		cmdclass = commands.get (cmdstring)
		if not cmdclass:
			raise CommandError ("Unknown command.")

		handler = handlers.get (cmdclass)
		if not handler:
			raise CommandError ("No handler found for command.")

		request = cmdclass.decode_request (fields)
		response = None
		session = self.create_session ()

		try:
			response = handler (request, session)
			if not isinstance (response, cmdclass.Response):
				raise CommandError ("Invalid response from handler.")
			encoded = cmdclass.encode_response (response)
			session.commit ()
		except:
			session.rollback ()
			raise

		return encoded
