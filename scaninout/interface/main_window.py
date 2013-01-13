import datetime
from gi.repository import GLib, GObject, Gdk, Gtk
from ..commands_base import CommandError, ValidationError
from ..types import Member, TagField
from .ui import BuilderWindow, WeakFunctionWrapper, WeakSignalWrapper
from . import client

class MainWindowScanner (GObject.GObject):

	__gsignals__ = {
		"attach": (GObject.SIGNAL_RUN_FIRST, None, []),
		"detach": (GObject.SIGNAL_RUN_LAST, None, []),
		"scan": (GObject.SIGNAL_RUN_LAST, bool, [str], GObject.signal_accumulator_true_handled),
	}

	def __init__ (self, window):

		GObject.GObject.__init__ (self)

		self.window = window
		self.gdkwindow = window.get_window ()
		self.scanners = set ()
		self.buffer = []

		WeakSignalWrapper (window, "map-event", self.window_mapped)
		WeakSignalWrapper (window, "unmap-event", self.window_unmapped)
		WeakSignalWrapper (window, "key-press-event", self.key_pressed)
		WeakSignalWrapper (window, "key-release-event", self.key_released)

		devman = window.get_display ().get_device_manager ()
		WeakSignalWrapper (devman, "device-added", self.device_added)
		WeakSignalWrapper (devman, "device-removed", self.device_removed)

	def enumerate (self):
		devman = self.window.get_display ().get_device_manager ()
		for device in devman.list_devices (Gdk.DeviceType.SLAVE):
			self.device_added (devman, device)
	
	@property
	def attached (self):
		return len (self.scanners) > 0
	
	def window_mapped (self, window, event):
		self.gdkwindow = window.get_window ()
		for scanner in self.scanners:
			self._grab (scanner)

	def window_unmapped (self, window, event):
		self.gdkwindow = window.get_window ()
		for scanner in self.scanners:
			self._ungrab (scanner)

	def key_pressed (self, window, event):
		if event.get_source_device () in self.scanners:
			self.process_key (event.string)
			return True
		else:
			return False

	def key_released (self, window, event):
		if event.get_source_device () in self.scanners:
			return True
		else:
			return False

	def device_added (self, devman, device):
		if (
			device.get_source () == Gdk.InputSource.KEYBOARD and
			device.get_device_type () == Gdk.DeviceType.SLAVE and
			" Barcode " in device.get_name () and
			device not in self.scanners
		):
			self.scanners.add (device)
			self._grab (device)
			if len (self.scanners) == 1:
				self.emit ("attach")

	def device_removed (self, devman, device):
		if device in self.scanners:
			self._ungrab (device)
			self.scanners.remove (device)
			if len (self.scanners) == 0:
				self.emit ("detach")

	def _grab (self, device):

		if self.gdkwindow is None:
			return

		grabbed = False
		while not grabbed:
			device.set_mode (Gdk.InputMode.SCREEN)
			grabbed = (device.grab (
				self.gdkwindow, Gdk.GrabOwnership.NONE,
				False, Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.KEY_RELEASE_MASK,
				None, 0
			) == Gdk.GrabStatus.SUCCESS)
		Gtk.device_grab_add (self.window, device, False)

	def _ungrab (self, device):
		pass

	def process_key (self, key):
		if key in ['\r', '\n', '\r\n']:
			self.emit ("scan", ''.join (self.buffer))
			del self.buffer[:]
		else:
			self.buffer.append (key)
	
class MainWindow (BuilderWindow):

	ui_file = "main.glade"
	ui_name = "window"

	def __init__ (self):

		BuilderWindow.__init__ (self)

		self.scanner = MainWindowScanner (self)
		self.scanner_detached (self.scanner)
		WeakSignalWrapper (self.scanner, "attach", self.scanner_attached)
		WeakSignalWrapper (self.scanner, "detach", self.scanner_detached)
		WeakSignalWrapper (self.scanner, "scan", self.scanner_scanned,
			after=True)
		self.scanner.enumerate ()

		self.time_format = self.objects.time_label.get_text ()
		GLib.idle_add (lambda: self.tick () and False)
		GLib.timeout_add (250, WeakFunctionWrapper (self.tick))

		self.objects.name_label.set_text ("")
		self.objects.inout_label.set_text ("")

		WeakSignalWrapper (self.objects.actions_quit_item, "activate",
			self.actions_quit_activated)

	def tick (self):

		self.objects.time_label.set_text (datetime.datetime.now ().strftime (
			"%A, %B %d, %Y\n%I:%M:%S %p"
		))

		try:
			client.ping ()
		except IOError:
			self.objects.lower_label.set_markup ('<span foreground="red">Cannot connect to server.</span>')
		else:
			self.objects.lower_label.set_markup ('<span>Remember to sign out!</span>')

		return True

	def scanner_attached (self, scanner):
		self.objects.upper_label.set_markup ('<span>Scan your ID now.</span>')

	def scanner_detached (self, scanner):
		self.objects.upper_label.set_markup ('<span foreground="red">No scanner found.</span>')

	def scanner_scanned (self, scanner, tag):

		try:
			TagField ().validate (tag)
		except ValidationError:
			return

		try:
			client.member_scan_in_out (tag=tag)
		except CommandError as e:
			if e.id == "member-not-found":
				from .member_windows import MemberEditDialog
				dialog = MemberEditDialog (
					scanner=self.scanner,
					tag=tag
				)
				dialog.show_all ()
				dialog.run ()
				dialog.destroy ()
			else:
				raise
			return

		raise 2

	def actions_quit_activated (self, window):
		self.destroy ()
