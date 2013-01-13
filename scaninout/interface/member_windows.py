from gi.repository import Gtk
from ..types import Member
from ..commands_base import ValidationError
from . import client
from .ui import BuilderDialog, WeakSignalWrapper

class MemberEditDialog (BuilderDialog):

	ui_file = "member_edit.glade"
	ui_name = "dialog"

	def __init__ (self, scanner, member=None, tag=None):

		self.member = member or Member ()

		WeakSignalWrapper (self.objects.ok_button, "clicked", self.ok_clicked)
		WeakSignalWrapper (self.objects.cancel_button, "clicked", self.cancel_clicked)

		self.row_count = 0

		self.tag_entry = Gtk.Entry ()
		self.tag_entry.set_editable (False)
		self.tag_entry.set_can_focus (False)
		self.tag_entry.set_placeholder_text ("[Scan ID to set]")
		self.tag_entry.set_text (tag or member.tag or "")
		self.add_row ("Tag", self.tag_entry)

		self.objects.form_grid.attach (Gtk.Separator.new (Gtk.Orientation.HORIZONTAL),
			0, self.row_count, 2, 1)
		self.row_count += 1

		self.first_name_entry = Gtk.Entry ()
		self.add_row ("First Name", self.first_name_entry)
		self.last_name_entry = Gtk.Entry ()
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
		m.tag = self.tag_entry.get_text ()
		m.first_name = self.first_name_entry.get_text ()
		m.last_name = self.last_name_entry.get_text ()

	def ok_clicked (self, button):
		if self.member.id is not None:
			client.member_edit (member=self.member)
		else:
			client.member_add (member=self.member)

	def cancel_clicked (self, button):
		pass

	def entry_changed (self, entry):
		self.check_valid ()
