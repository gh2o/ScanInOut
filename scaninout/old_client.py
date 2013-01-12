from collections import deque
from gi.repository import GObject, Gio, GLib

from . import DEFAULT_SOCKET_PATH
from . import types

class Client (GObject.GObject):

	__gsignals__ = {
		"connect": (GObject.SIGNAL_RUN_FIRST, None, []),
		"disconnect": (GObject.SIGNAL_RUN_LAST, None, []),
	}

	def __init__ (self, sockpath=DEFAULT_SOCKET_PATH):

		GObject.GObject.__init__ (self)
		self.sockpath = sockpath

		self.tohandle = None
		self.socket = None
	
	def connect (self):

		# give up if already connected
		if self.socket is not None:
			return

		# cancel previous timeout
		if self.tohandle is not None:
			GLib.source_remove (self.tohandle)
			self.tohandle = None

		# do the connect
		sock = Gio.Socket.new (Gio.SocketFamily.UNIX, Gio.SocketType.STREAM,
			Gio.SocketProtocol.DEFAULT)

		try:
			sock.connect (Gio.UnixSocketAddress.new (self.sockpath), None)
		except RuntimeError as e:
			sock.close ()
			self.tohandle = GLib.timeout_add (100, lambda: self.connect () and False)
			return

		self.socket = sock
		self.emit ("connect")
	
	def disconnect (self):

		# cancel previous timeout
		if self.tohandle is not None:
			GLib.source_remove (self.tohandle)
			self.tohandle = None

		# give up if not connected
		if self.socket is None:
			return

		# do the disconnect
		self.emit ("disconnect")
		self.socket.close ()
		self.socket = None
