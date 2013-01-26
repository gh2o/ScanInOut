from gi.repository import Gtk
from ..types import Member
from ..commands_base import ValidationError
from .ui import BuilderDialog, WeakSignalWrapper
from . import scanner

class MemberEditDialog (BuilderDialog):

	ui_file = "member_edit.glade"
	ui_name = "dialog"

	def __init__ (self, client, member=None, tag=None):

		BuilderDialog.__init__ (self)
		if member is not None:
			self.set_title ('Edit "%s"' % member.name)
		else:
			self.set_title ('Add Member')

		self.client = client
		self.member = member or Member ()

		WeakSignalWrapper (self.objects.ok_button, "clicked", self.ok_clicked)
		WeakSignalWrapper (self.objects.cancel_button, "clicked", self.cancel_clicked)

		self.connect ("destroy", self.object_destroyed)
		self.scanner_scanned_handle = scanner.connect ("scan", self.scanner_scanned)

		self.row_count = 0

		self.tag_entry = Gtk.Entry ()
		self.tag_entry.set_editable (False)
		self.tag_entry.set_can_focus (False)
		self.tag_entry.set_placeholder_text ("[Scan ID to set]")
		self.tag_entry.set_text (tag or "")
		self.add_row ("Tag", self.tag_entry)

		self.objects.form_grid.attach (Gtk.Separator.new (Gtk.Orientation.HORIZONTAL),
			0, self.row_count, 2, 1)
		self.row_count += 1

		self.first_name_entry = Gtk.Entry ()
		self.first_name_entry.set_text (self.member.first_name or "")
		self.add_row ("First Name", self.first_name_entry)
		self.last_name_entry = Gtk.Entry ()
		self.last_name_entry.set_text (self.member.last_name or "")
		self.add_row ("Last Name", self.last_name_entry)

		self.check_valid ()

	def add_row (self, name, entry):

		label = Gtk.Label (name)

		label.set_vexpand (True)
		entry.set_vexpand (True)
		entry.set_hexpand (True)
		entry.set_activates_default (True)
		WeakSignalWrapper (entry, "changed", self.entry_changed)

		self.objects.form_grid.attach (label, 0, self.row_count, 1, 1)
		self.objects.form_grid.attach (entry, 1, self.row_count, 1, 1)
		self.row_count += 1
	
	def check_valid (self):

		ok_button = self.objects.ok_button
		self.populate_member ()
		try:
			self.member.validate_object ()
		except ValidationError:
			ok_button.set_sensitive (False)
		else:
			ok_button.set_sensitive (True)
	
	def populate_member (self):

		m = self.member
		m.first_name = self.first_name_entry.get_text ().strip ()
		m.last_name = self.last_name_entry.get_text ().strip ()
		
		tag = self.tag_entry.get_text ().strip ()
		if tag:
			m.tag = tag
	
	def scanner_scanned (self, scanner, data):

		self.tag_entry.set_text (data)
		self.entry_changed (self.tag_entry)
		return True

	def ok_clicked (self, button):
		if self.member.id is not None:
			self.client.member_edit (member=self.member)
		else:
			self.client.member_add (member=self.member)

	def cancel_clicked (self, button):
		pass

	def entry_changed (self, entry):
		self.check_valid ()

	def object_destroyed (self, obj):
		scanner.disconnect (self.scanner_scanned_handle)
