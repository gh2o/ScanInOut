import os
import sys

def main (args):
	
	### PARSE OPTIONS

	from optparse import OptionParser, IndentedHelpFormatter
	from .. import DEFAULT_SOCKET_PATH

	parser = OptionParser (
		usage="%prog [options]",
		formatter=IndentedHelpFormatter (max_help_position=40)
	)
	parser.add_option ('-s', '--socket', dest='socket',
		help="socket path", metavar="SOCKET", default=DEFAULT_SOCKET_PATH)

	options, args = parser.parse_args (args)

	### DEFAULT SIGNAL HANDLER

	import signal
	signal.signal (signal.SIGINT, signal.SIG_DFL)

	### LOAD AND START APPLICATION

	from gi.repository import Gtk, Gdk
	from .main_window import MainWindow
	window = MainWindow ()
	window.connect ("destroy", lambda win: Gtk.main_quit ())
	window.show_all ()
	Gtk.main ()
