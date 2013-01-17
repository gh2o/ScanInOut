import time
import datetime
import calendar
from collections import namedtuple
from gi.repository import GLib, GObject, Gdk, Gtk
from ..commands_base import CommandError, ValidationError
from ..client import AuthenticatedClient
from ..types import Member, TagField
from .ui import BuilderWindow, WeakFunctionWrapper, WeakSignalWrapper, format_duration
from . import scanner

class MainWindow (BuilderWindow):

	ui_file = "main.glade"
	ui_name = "window"

	SignedInRow = namedtuple ('SignedInRow', [
		'id', 'name',
		'start_time_epoch', 'duration_seconds',
		'start_time_text', 'duration_text'
	])

	def __init__ (self, client):

		BuilderWindow.__init__ (self)
		self.client = client

		self.scanner_detached (scanner)
		WeakSignalWrapper (scanner, "attach", self.scanner_attached)
		WeakSignalWrapper (scanner, "detach", self.scanner_detached)
		WeakSignalWrapper (scanner, "scan", self.scanner_scanned,
			after=True)

		self.objects.signedin_liststore.set_sort_column_id (
			self.SignedInRow._fields.index ("name"),
			Gtk.SortType.ASCENDING
		)

		self.time_format = self.objects.time_label.get_text ()
		self.objects.name_label.set_text ("")
		self.objects.inout_label.set_text ("")

		WeakSignalWrapper (self.objects.actions_manage_item, "activate",
			self.actions_manage_activated)
		WeakSignalWrapper (self.objects.actions_quit_item, "activate",
			self.actions_quit_activated)

		self.fade_handle = None

		self.signedin_scroll_handle = None
		WeakSignalWrapper (self.objects.signedin_vadjustment, "value-changed",
			self.signedin_list_scrolled)

		GLib.idle_add (lambda: self.update_signedin_list () and False)
		GLib.timeout_add (5000, WeakFunctionWrapper (self.update_signedin_list))
		GLib.idle_add (lambda: self.refresh_signedin_list () and False)
		GLib.timeout_add (500, WeakFunctionWrapper (self.refresh_signedin_list))

		self.tick ()
		GLib.timeout_add (250, WeakFunctionWrapper (self.tick))

	def tick (self):

		self.objects.time_label.set_text (datetime.datetime.now ().strftime (
			"%A, %B %d, %Y\n%I:%M:%S %p"
		))

		try:
			self.client.ping ()
		except IOError:
			self.objects.lower_label.set_markup ('<span foreground="red">Cannot connect to server.</span>')
		else:
			self.objects.lower_label.set_markup ('<span>Remember to scan out!</span>')

		return True

	def fade_info (self):
		self.objects.name_label.set_text ("")
		self.objects.inout_label.set_text ("")
		self.objects.just_completed_label.set_text ("")
		self.objects.total_hours_label.set_text ("")
	
	def signedin_list_scrolled (self, adj):
		if self.signedin_scroll_handle is not None:
			return
		self.signedin_scroll_handle = \
			GLib.timeout_add (50, self.signedin_list_scrolled_timeout)
	
	def signedin_list_scrolled_timeout (self):
		self.refresh_signedin_list ()
		self.signedin_scroll_handle = None
	
	def update_signedin_list (self):

		try:
			store = self.objects.signedin_liststore
			response = self.client.member_get_signed_in ()
		except IOError:
			return True

		old_dict = dict (
			(row.id, None)
				for row in (self.SignedInRow (*x) for x in store)
		)
		new_dict = dict (
			(member.id, (member, shift))
				for member, shift in response.member_shift_pairs
		)

		old_ids = set (old_dict.keys ())
		new_ids = set (new_dict.keys ())

		# get out if nothing changed

		if old_ids == new_ids:
			return True

		# something did change

		added_ids = new_ids - old_ids
		removed_ids = old_ids - new_ids

		# remove old ids
		for id in removed_ids:
			row = (x for x in store if self.SignedInRow (*x).id == id).next ()
			store.remove (row.iter)

		# add new ones
		for id in added_ids:
			member, shift = new_dict[id]
			store.append (self.SignedInRow (
				id = member.id,
				name = "",
				start_time_epoch = 0,
				duration_seconds = 0,
				start_time_text = "",
				duration_text = "",
			))

		# update them all
		for itrow in store:
			row = self.SignedInRow (*itrow)
			member, shift = new_dict[row.id]
			ste = calendar.timegm (shift.start_time.timetuple ())
			newrow = row._replace (
				name = member.name,
				start_time_epoch = ste,
				start_time_text = datetime.datetime.fromtimestamp (ste)
					.strftime ('%I:%M:%S %p'),
			)
			if row != newrow:
				store.set_row (itrow.iter, newrow)

		return True
	
	def refresh_signedin_list (self):
		store = self.objects.signedin_liststore
		for itrow in self.visible_signedin_list_rows ():
			row = self.SignedInRow (*itrow)
			secs = time.time () - row.start_time_epoch
			store.set_row (itrow.iter, row._replace (
				duration_seconds = secs,
				duration_text = format_duration (secs / 3600.),
			))
		return True

	def visible_signedin_list_rows (self):

		rg = self.objects.signedin_treeview.get_visible_range ()
		if rg is None:
			return

		start_path, end_path = rg
		store = self.objects.signedin_liststore

		row = store[store.get_iter (start_path)]
		while True:
			yield row
			row = row.next
			if row is None or row.path > end_path:
				break

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
			response = self.client.member_scan_in_out (tag=tag)
		except CommandError as e:
			if e.id == "member-not-found":
				# don't block while stdin is held by glib
				GLib.idle_add (self.scanner_scanned_add_member, tag)
			else:
				raise
			return

		if self.fade_handle is not None:
			GLib.source_remove (self.fade_handle)
		self.fade_handle = GLib.timeout_add (10000, self.fade_info)

		si = response.scanned_in
		self.objects.name_label.set_text (response.member.name)
		self.objects.inout_label.set_text (["OUT", "IN"][si])
		self.objects.just_completed_label.set_text (
			"" if si else format_duration (response.elapsed_hours))
		self.objects.total_hours_label.set_text (
			"" if si else format_duration (response.total_hours))

		self.update_signedin_list ()

		return True

	def scanner_scanned_add_member (self, tag):

		from .member_windows import MemberEditDialog
		dialog = MemberEditDialog (client=self.client, tag=tag)
		dialog.show_all ()
		res = dialog.run ()
		dialog.destroy ()

		if res == Gtk.ResponseType.OK:
			self.scanner_scanned (scanner, tag)

	def actions_manage_activated (self, item):

		from .management_windows import (
			ManagementPasswordDialog, ManagementMainDialog)
		dialog = ManagementPasswordDialog ()
		dialog.set_transient_for (self)
		dialog.show_all ()

		authclient = None
		while True:

			res = dialog.run ()
			if res != Gtk.ResponseType.OK:
				break

			try:
				authclient = AuthenticatedClient (password=dialog.password)
				authclient.authenticated_ping ()
			except CommandError as e:
				authclient = None
				if e.id != "invalid-signature":
					raise
			else:
				break

			dialog.mark_incorrect ()

		dialog.destroy ()
		if authclient is None:
			return

		dialog = ManagementMainDialog (client=authclient)
		dialog.set_transient_for (self)
		dialog.show_all ()
		dialog.run ()
		dialog.destroy ()

	def actions_quit_activated (self, item):
		self.destroy ()
