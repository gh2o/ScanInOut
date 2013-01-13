import json
import sqlalchemy
import sqlalchemy.orm

from ..commands_base import Command, CommandError
from ..commands import commands
from ..rpc import RPCRequest, RPCResponse
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

			ret = None
			ferr = CommandError ("format-error", "Format error.")

			try:

				try:
					obj = json.loads (raw)
				except ValueError as e:
					raise CommandError ("json-error", "JSON error: " + str (e))

				try:
					rpcreq = RPCRequest.decode_from_base (obj)
				except:
					raise CommandError ("decode-error", "Decode error.")

				ret = self.handle_request (rpcreq)

			except CommandError as e:

				ret = RPCResponse (
					success = False,
					error = e,
				)

			except:

				e = CommandError ("critical-error", "Critical error. See log for details.")
				ret = RPCResponse (
					success = False,
					error = e,
				)

				import traceback
				traceback.print_exc ()

			wfile.write (json.dumps (ret.encode_to_base ()) + "\n")
	
	def handle_request (self, rpcreq):

		cmdclass = commands.get (rpcreq.command)
		if not cmdclass:
			raise CommandError ("unknown-command", "Unknown command.")

		handler = handlers.get (cmdclass)
		if not handler:
			raise CommandError ("no-handler", "No handler found for command.")

		request = cmdclass.decode_request (rpcreq.fields)
		response = None
		session = self.create_session ()

		try:
			response = handler (request, session)
			if not isinstance (response, cmdclass.Response):
				raise CommandError ("no-response", "Invalid response from handler.")
			ret = RPCResponse (
				success = True,
				fields = cmdclass.encode_response (response)
			)
			session.commit ()
		except:
			session.rollback ()
			raise

		return ret
