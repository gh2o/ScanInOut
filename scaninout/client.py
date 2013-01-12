import json
import socket

from . import DEFAULT_SOCKET_PATH
from . import commands
from .commands_base import CommandError

class ClientFunction (object):

	def __init__ (self, client, cmdclass):
		self.client = client
		self.cmdclass = cmdclass
	
	def __call__ (self, **kwargs):
		request = self.cmdclass.Request (**kwargs)
		return self.client.call (self.cmdclass, request)
	
	def __repr__ (self):
		return '<client function %s>' % self.cmdclass.__name__

class Client (object):

	__slots__ = ["sockpath", "sockfile"]

	def __init__ (self, sockpath=DEFAULT_SOCKET_PATH):
		self.sockpath = sockpath
		self.sockfile = None
	
	def __getattr__ (self, name):
		try:
			cmdclass = commands.commands_underscored[name]
		except KeyError:
			raise AttributeError
		return ClientFunction (self, cmdclass)
	
	def __exchange (self, data):
		self.sockfile.write (data + "\n")
		self.sockfile.flush ()
		return self.sockfile.readline ()
	
	def call (self, cmdclass, request):

		senddata = json.dumps ({
			"command": cmdclass.__name__,
			"fields": request.encode_to_json (),
		})

		try:
			recvdata = self.__exchange (senddata)
		except:
			sock = socket.socket (socket.AF_UNIX, socket.SOCK_STREAM, 0)
			sock.connect (self.sockpath)
			self.sockfile = sock.makefile ('r+')
			recvdata = self.__exchange (senddata)

		itm = json.loads (recvdata)
		if not itm["success"]:
			raise CommandError ("command error: %s" % itm["message"])

		return cmdclass.Response.decode_from_json (itm["fields"])
