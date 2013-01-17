import binascii
import json
import socket

from . import DEFAULT_SOCKET_PATH
from . import commands
from .commands_base import CommandError
from .rpc import RPCRequest, RPCResponse
from .utils import generate_pwhash, generate_signature

def camelize (name):
	buf = []
	nextup = True
	for index, char in enumerate (name):
		if nextup:
			buf.append (char.upper ())
			nextup = False
		elif char == '_':
			nextup = True
		else:
			buf.append (char)
	return ''.join (buf)

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
			cmdclass = commands.commands[camelize(name)]
		except KeyError:
			raise AttributeError
		return ClientFunction (self, cmdclass)
	
	def __exchange_sub (self, data):

		self.sockfile.write (data + "\n")
		self.sockfile.flush ()

		ret = self.sockfile.readline ()
		if ret[-1] == '\n':
			ret = ret[:-1]
		if ret[-1] == '\r':
			ret = ret[:-1]

		return ret

	def exchange (self, data):

		try:
			return self.__exchange_sub (data)
		except:
			sock = socket.socket (socket.AF_UNIX, socket.SOCK_STREAM, 0)
			sock.connect (self.sockpath)
			self.sockfile = sock.makefile ('r+')
			return self.__exchange_sub (data)

	def call (self, cmdclass, request):

		senddata = self.encode_request_to_json (cmdclass, request)
		recvdata = self.exchange (senddata)
		ret = self.decode_request_from_json (cmdclass, recvdata)
		return ret

	def encode_request_to_json (self, cmdclass, request):
		return json.dumps (RPCRequest (
			command = cmdclass.__name__,
			fields = cmdclass.encode_request (request)
		).encode_to_base ())
	
	def decode_request_from_json (self, cmdclass, recvdata):
		rpcres = RPCResponse.decode_from_base (json.loads (recvdata))
		if not rpcres.success:
			raise rpcres.error
		return cmdclass.decode_response (rpcres.fields)

class AuthenticatedClient (Client):
	
	__slots__ = ["pwhash"]

	def __init__ (self, password, **kwargs):
		Client.__init__ (self, **kwargs)
		self.pwhash = generate_pwhash (password)
	
	def call (self, cmdclass, request):

		senddata = self.encode_request_to_json (cmdclass, request)

		GN = commands.GenerateNonce
		nonce = binascii.unhexlify (Client.call (self, GN, GN.Request ()).nonce_hex)
		signature = generate_signature (self.pwhash, nonce, senddata)
		PS = commands.PreloadSignature
		Client.call (self, PS, PS.Request (signature_hex=binascii.hexlify (signature)))

		recvdata = self.exchange (senddata)
		ret = self.decode_request_from_json (cmdclass, recvdata)
		return ret
