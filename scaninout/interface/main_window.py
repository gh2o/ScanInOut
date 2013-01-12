import datetime
from gi.repository import GLib, GObject, Gdk, Gtk
from .ui import BuilderWindow, WeakFunctionWrapper, WeakSignalWrapper

class MainWindowScanner (GObject.GObject):

	__gsignals__ = {
		"scanner-added": (GObject.SIGNAL_RUN_FIRST, None, []),
		"scanner-removed": (GObject.SIGNAL_RUN_LAST, None, []),
		"scanner-scanned": (GObject.SIGNAL_RUN_LAST, bool, [str], GObject.signal_accumulator_true_handled),
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
				self.emit ("scanner-added")

	def device_removed (self, devman, device):
		if device in self.scanners:
			self._ungrab (device)
			self.scanners.remove (device)
			if len (self.scanners) == 0:
				self.emit ("scanner-removed")

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
			self.emit ("scanner-scanned", ''.join (self.buffer))
			del self.buffer[:]
		else:
			self.buffer.append (key)
	
class MainWindow (BuilderWindow):

	ui_file = "main.glade"
	ui_name = "window"

	def __init__ (self):

		BuilderWindow.__init__ (self)

		self.scanner_removed ()
		self.scanner = MainWindowScanner (self)
		WeakSignalWrapper (self.scanner, "scanner-added", self.scanner_added)
		WeakSignalWrapper (self.scanner, "scanner-removed", self.scanner_removed)
		WeakSignalWrapper (self.scanner, "scanner-scanned", self.scanner_scanned)
		self.scanner.enumerate ()

		self.time_format = self.objects.time_label.get_text ()
		self.tick ()
		GLib.timeout_add (250, WeakFunctionWrapper (self.tick))

		self.objects.name_label.set_text ("")
		self.objects.inout_label.set_text ("")

		WeakSignalWrapper (self.objects.actions_quit_item, "activate",
			self.actions_quit_activated)

	def tick (self):
		self.objects.time_label.set_text (datetime.datetime.now ().strftime (
			"%A, %B %d, %Y\n%I:%M:%S %p"
		))
		return True

	def scanner_added (self):
		self.objects.instruction_label.set_markup ('Scan your ID now.')

	def scanner_removed (self):
		self.objects.instruction_label.set_markup ('<span foreground="red">No scanner found.</span>')

	def scanner_scanned (self, data):
		print repr (data)
		pass

	def actions_quit_activated (self, window):
		self.destroy ()
