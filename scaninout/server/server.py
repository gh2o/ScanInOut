import binascii
import json
import sqlalchemy
import sqlalchemy.orm

from ..commands_base import Command, CommandError
from ..commands import commands
from ..rpc import RPCRequest, RPCResponse
from ..utils import generate_signature
from .. import settings
from .handlers import handlers
from .db import metadata as db_metadata

password_hash = binascii.unhexlify (settings.password_hash_hex)

class Connection (object):

	def __init__ (self, server, sock):
		self.server = server
		self.rfile = sock.makefile ('r', -1)
		self.wfile = sock.makefile ('w', 0)
		self.nonce = None
		self.signature = None
	
	def handle_connection (self):

		while True:

			raw = self.rfile.readline ()
			if not raw:
				break

			if raw[-1] == '\n':
				raw = raw[:-1]
			if raw[-1] == '\r':
				raw = raw[:-1]

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

				ret = self.handle_request (rpcreq, raw)

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

			self.wfile.write (json.dumps (ret.encode_to_base ()) + "\n")
	
	def handle_request (self, rpcreq, raw):

		cmdclass = commands.get (rpcreq.command)
		if not cmdclass:
			raise CommandError ("unknown-command", "Unknown command.")

		handler = handlers.get (cmdclass)
		if not handler:
			raise CommandError ("no-handler", "No handler found for command.")

		if not getattr (handler, "public", False):
			self.check_signature (raw)

		request = cmdclass.decode_request (rpcreq.fields)
		response = None
		session = self.server.create_session ()

		try:
			response = handler (request, session, self)
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

	def check_signature (self, raw):

		if self.nonce is None or self.signature is None:
			raise CommandError ("forbidden", "Command forbidden.")

		actual = generate_signature (password_hash, self.nonce, raw)
		if actual != self.signature:
			raise CommandError ("invalid-signature", "Invalid signature.")

		self.nonce = None
		self.signature = None

class Server (object):

	def __init__ (self, dbpath):
		self.dbpath = dbpath
		self.db = sqlalchemy.create_engine ("sqlite:///" + dbpath, echo=True)
		self.create_session = sqlalchemy.orm.sessionmaker (bind=self.db)
		db_metadata.bind = self.db
		db_metadata.create_all ()

	def handle_connection (self, sock, addr):
		conn = Connection (self, sock)
		conn.handle_connection ()
