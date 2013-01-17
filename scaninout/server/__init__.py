import os
import sys

def main (args):
	
	### PARSE OPTIONS

	from optparse import OptionParser, IndentedHelpFormatter
	from .. import DEFAULT_SOCKET_PATH

	parser = OptionParser (
		usage="%prog [options] dbpath",
		formatter=IndentedHelpFormatter (max_help_position=40)
	)
	parser.add_option ('-s', '--socket', dest='socket',
		help="socket path", metavar="SOCKET", default=DEFAULT_SOCKET_PATH)
	parser.add_option ('-e', '--echo', dest='echo',
		help='echo SQL commands', default=False, action="store_true")
	parser.add_option ('-u', '--user', dest='user',
		help="user to run as", metavar="USER")

	options, args = parser.parse_args (args)
	if len (args) < 1:
		print >>sys.stderr, "Database path must be specified."
		return 1

	dbpath, = args

	### DROP PRIVILEGES

	if options.user is not None:
		import pwd
		sp = pwd.getpwnam (options.user)
		os.setregid (sp.pw_gid, sp.pw_gid)
		os.setreuid (sp.pw_uid, sp.pw_uid)

	### PATCH GEVENT

	from gevent import monkey
	monkey.patch_all ()

	### BUILD SERVER

	from .server import Server
	server = Server (dbpath = dbpath, echo = options.echo)

	### BIND TO SOCKET

	try:
		os.unlink (options.socket)
	except OSError:
		pass

	import socket
	sock = socket.socket (socket.AF_UNIX, socket.SOCK_STREAM, 0)
	sock.bind (options.socket)
	sock.listen (16)
	sock.setblocking (False)
	os.chmod (options.socket, 0777)

	### START SERVER

	from gevent.server import StreamServer
	ss = StreamServer (sock, server.handle_connection)
	ss.serve_forever ()
