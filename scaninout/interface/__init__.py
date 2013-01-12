import os
import sys

client = None

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

	### ERROR HANDLER

	from gi.repository import Gtk, Gdk, Pango
	import traceback

	old_excepthook = sys.excepthook
	def new_excepthook (tp, val, tb):
		dialog = Gtk.MessageDialog (buttons=Gtk.ButtonsType.CLOSE, message_format="Error occurred!")
		dialog.format_secondary_text ("%s: %s" % (tp.__name__, val))
		tbbuf = Gtk.TextBuffer ()
		tbbuf.set_text ("".join (traceback.format_tb (tb)).rstrip ())
		tbtv = Gtk.TextView ()
		tbtv.set_buffer (tbbuf)
		tbtv.modify_font (Pango.font_description_from_string ("monospace 8"))
		tbscr = Gtk.ScrolledWindow ()
		tbscr.add (tbtv)
		tbscr.set_shadow_type (Gtk.ShadowType.IN)
		dialog.get_content_area ().pack_end (tbscr, True, True, 4)
		dialog.set_size_request (600, 500)
		dialog.show_all ()
		dialog.run ()
		dialog.destroy ()
		return old_excepthook (tp, val, tb)
	sys.excepthook = new_excepthook

	### SET UP CLIENT AND PING

	from ..client import Client
	global client
	client = Client ()

	### LOAD AND START APPLICATION

	from .main_window import MainWindow
	window = MainWindow ()
	window.connect ("destroy", lambda win: Gtk.main_quit ())
	window.show_all ()
	Gtk.main ()
