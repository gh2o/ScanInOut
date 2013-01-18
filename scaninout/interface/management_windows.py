import math
import datetime
import time
import csv
import textwrap
import calendar
from collections import namedtuple
from gi.repository import Gtk, Gdk, GLib
from ..utils import escape_xml
from .ui import BuilderDialog, WeakSignalWrapper, format_duration, format_date
from .member_windows import MemberEditDialog

class Exporter (object):
	def plain_writer (self, fd):
		return csv.writer (fd)
	def dict_writer (self, fd, fields):
		return csv.DictWriter (fd, fields)
	def export (self, client, filename):
		with open (filename, "w") as fd:
			self.export_impl (client, fd)

class TotalHoursExporter (Exporter):

	def export_impl (self, client, fd):

		writer = self.plain_writer (fd)
		writer.writerow (["First Name", "Last Name", "Hours", "Formatted Hours"])

		rp = client.member_get_all (with_shifts=True)
		for member, shifts in zip (rp.members, rp.shifts_lists):
			hours = sum (s.hours for s in shifts)
			writer.writerow ([
				member.first_name,
				member.last_name,
				hours,
				format_duration (hours)
			])

class WeeklyExporter (Exporter):

	def export_impl (self, client, fd):

		num_weeks = 100
		week_letters = 'SMTWTFS'

		# get start of week
		weekstart = datetime.datetime.now ()
		while weekstart.weekday () != 6: # make it sunday
			weekstart -= datetime.timedelta (days=1)
		weekstart = weekstart.replace (hour=0, minute=0, second=0, microsecond=0)
		weekstartepoch = time.mktime (weekstart.timetuple ())

		week = datetime.timedelta (days = 7)
		cols = ['First Name', 'Last Name']
		for bk in xrange (num_weeks):
			cols.append ((weekstart - bk * week).strftime ('Week of %m/%d/%Y'))

		writer = self.plain_writer (fd)
		writer.writerow (cols)

		rp = client.member_get_all (with_shifts=True)
		for member, shifts in zip (rp.members, rp.shifts_lists):
			dates = set (
				datetime.datetime.fromtimestamp (
					calendar.timegm (s.start_time.timetuple ())
				).date () for s in shifts
			)
			row = [member.first_name, member.last_name]
			rvals = [['-'] * 7 for _ in xrange (num_weeks)]
			for dt in dates:
				diff = weekstartepoch - time.mktime (dt.timetuple ())
				# round up to nearest week
				weekindex = int (math.ceil (float (diff) / (60 * 60 * 24 * 7)))
				if weekindex >= num_weeks:
					continue
				# set rvals with weekday
				wd = (dt.weekday () + 1) % 7 # convert to Sunday = 0
				rvals[weekindex][wd] = week_letters[wd]
			row.extend (''.join (rval) for rval in rvals)
			writer.writerow (row)
				
class ManagementPasswordDialog (BuilderDialog):

	ui_file = 'management_password.glade'
	ui_name = 'dialog'

	def __init__ (self):
		BuilderDialog.__init__ (self)
		WeakSignalWrapper (self.objects.password_entry, "changed", self.entry_changed)
		self.password = ""
		self.refresh ()
	
	def refresh (self):
		self.set_response_sensitive (Gtk.ResponseType.OK, bool (self.password))
	
	def mark_incorrect (self):
		self.objects.password_entry.delete_text (0, -1)
		self.objects.password_entry.set_icon_from_stock (Gtk.EntryIconPosition.SECONDARY,
			'gtk-dialog-error')
		self.objects.password_entry.set_icon_tooltip_text (Gtk.EntryIconPosition.SECONDARY,
			"Incorrect password.")
		self.objects.password_entry.grab_focus ()
	
	def entry_changed (self, entry):
		self.objects.password_entry.set_icon_from_stock (Gtk.EntryIconPosition.SECONDARY, None)
		self.password = self.objects.password_entry.get_text ()
		self.refresh ()
	
class ManagementMainDialog (BuilderDialog):

	ui_file = 'management_main.glade'
	ui_name = 'dialog'

	MemberRow = namedtuple ("MemberRow", [
		"id", "name",
		"first_name", "last_name",
		"last_start_epoch", "last_start_text",
		"total_duration_seconds", "total_duration_text",
		"background_color"
	])

	info_label_template = textwrap.dedent ("""\
		<span size="large" weight="bold">%(name)s</span>
	""".rstrip ())

	def __init__ (self, client):

		BuilderDialog.__init__ (self)
		self.client = client

		# Member

		self.store = self.objects.members_liststore
		self.store.set_sort_column_id (
			self.MemberRow._fields.index ("first_name"),
			Gtk.SortType.ASCENDING
		)

		GLib.idle_add (self.reload_members_list)
		WeakSignalWrapper (self.objects.refresh_button, "clicked",
			self.refresh_clicked)

		self.reload_from_selection ()
		WeakSignalWrapper (self.objects.members_selection, "changed",
			self.selection_changed)

		WeakSignalWrapper (self.objects.add_button, "clicked", self.add_clicked)
		WeakSignalWrapper (self.objects.edit_button, "clicked", self.edit_clicked)
		WeakSignalWrapper (self.objects.delete_button, "clicked", self.delete_clicked)

		WeakSignalWrapper (self.objects.members_treeview, "row-activated", self.row_activated)

		# Export

		WeakSignalWrapper (self.objects.export_button, "clicked", self.export_clicked)
	
	def get_selected_member (self):

		it = self.objects.members_selection.get_selected()[1]
		if it is None:
			return None

		return self.client.member_get (
			id = self.MemberRow (*self.store[it]).id
		).member
	
	def reload_members_list (self):

		self.objects.members_selection.set_mode (Gtk.SelectionMode.NONE)

		rp = self.client.member_get_all (with_shifts=True)
		members_shifts_lists = zip (rp.members, rp.shifts_lists)

		store = self.store
		store.clear ()

		for member, shifts in members_shifts_lists:
			shifts.sort (key=lambda s: s.start_time)
			total_hours = sum (x.hours for x in shifts)
			last_shift = shifts[-1] if shifts else None
			row = self.MemberRow (
				id = member.id,
				name = member.name,
				first_name = member.first_name,
				last_name = member.last_name,
				last_start_epoch = calendar.timegm (last_shift.start_time.timetuple ())
					if last_shift is not None else 0,
				last_start_text = format_date (last_shift.start_time)
					if last_shift is not None else "-",
				total_duration_seconds = total_hours * 3600,
				total_duration_text = format_duration (total_hours),
				background_color = None
			)
			store.append (row)

		self.objects.members_selection.set_mode (Gtk.SelectionMode.SINGLE)
	
	def reload_from_selection (self):

		member = self.get_selected_member ()
		self.objects.edit_button.set_sensitive (member is not None)
		self.objects.delete_button.set_sensitive (member is not None)

		if member is None:
			self.objects.right_tabs.set_no_show_all (True)
			self.objects.right_tabs.hide ()
			self.objects.info_label.set_markup (
				'<span weight="bold" size="large" foreground="dimgrey">' +
				'Select a member.' +
				'</span>'
			)
		else:
			self.objects.right_tabs.set_no_show_all (False)
			self.objects.right_tabs.show ()

			self.objects.info_label.set_markup (self.info_label_template % {
				"name": member.name,
			})
	
	def add_clicked (self, button):

		dialog = MemberEditDialog (client=self.client)
		dialog.set_transient_for (self)
		dialog.show_all ()
		res = dialog.run ()
		dialog.destroy ()

		if res == Gtk.ResponseType.OK:
			self.reload_members_list ()

	def edit_clicked (self, button):

		member = self.get_selected_member ()
		if member is None:
			return

		dialog = MemberEditDialog (client=self.client, member=member)
		dialog.set_transient_for (self)
		dialog.show_all ()
		res = dialog.run ()
		dialog.destroy ()

		if res == Gtk.ResponseType.OK:
			self.reload_members_list ()

	def delete_clicked (self, button):

		member = self.get_selected_member ()

		dialog = Gtk.MessageDialog (
			parent = self,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.QUESTION,
			message_format = 'Delete %s (and all of his/her hours)?' % member.name
		)
		dialog.add_buttons (
			Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_DELETE, Gtk.ResponseType.OK
		)
		res = dialog.run ()
		dialog.destroy ()

		if res == Gtk.ResponseType.OK:
			self.client.member_delete (id=member.id)
			self.reload_members_list ()
	
	def refresh_clicked (self, button):
		self.reload_members_list ()

	def selection_changed (self, selection):
		self.reload_from_selection ()
	
	def row_activated (self, tv):
		self.edit_clicked (None)
	
	def export_clicked (self, button):

		exporter = None
		if self.objects.total_hours_radio.get_active ():
			exporter = TotalHoursExporter ()
		elif self.objects.weekly_attendance_radio.get_active ():
			exporter = WeeklyExporter ()

		if exporter is None:
			return

		dialog = Gtk.FileChooserDialog (
			title = "Export",
			parent = self,
			action = Gtk.FileChooserAction.SAVE,
			buttons = [
				Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
				Gtk.STOCK_SAVE, Gtk.ResponseType.OK
			]
		)
		dialog.set_local_only (True)
		dialog.set_select_multiple (False)
		res = dialog.run ()
		fn = dialog.get_filename ()

		if res == Gtk.ResponseType.OK:
			exporter.export (self.client, fn)

		dialog.destroy ()
