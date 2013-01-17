import os
import datetime
import weakref
import types
from gi.repository import Gtk, GObject

UI_LOCATION = os.path.dirname (os.path.realpath (__file__)) + "/ui"

def format_date (dt):
	return dt.strftime ("%m/%d/%Y %I:%M:%S %p")

def format_duration (hours):
	secs = int (hours * 3600)
	return "%d:%02d:%02d" % (
		secs / 3600,
		(secs / 60) % 60,
		secs % 60
	)

class WeakFunctionWrapper (object):

	def __init__ (self, func, final=False):
		self.final = final
		if isinstance (func, types.MethodType):
			self.objref = weakref.ref (func.im_self)
			self.funcref = weakref.ref (func.im_func)
		else:
			self.objref = None
			self.funcref = weakref.ref (func)
	
	def __call__ (self, *args, **kwargs):
		if self.objref is not None:
			obj = self.objref ()
			func = self.funcref ()
			if obj is not None and func is not None:
				return func (obj, *args, **kwargs)
			else:
				return self.final
		else:
			func = self.funcref ()
			if func is not None:
				return func (*args, **kwargs)
			else:
				return self.final

class WeakSignalWrapper (object):

	__subfinal = object ()

	def __init__ (self, target, signal, func, after=False, final=False):
		self.wrapper = WeakFunctionWrapper (func, self.__subfinal)
		self.final = final
		self.targetref = weakref.ref (target)
		self.handle = [target.connect, target.connect_after][after](signal, self)
	
	def __call__ (self, *args, **kwargs):
		ret = self.wrapper (*args, **kwargs)
		if ret is not self.__subfinal:
			return ret
		else:
			target = self.targetref ()
			if target is not None:
				target.disconnect (self.handle)
			return self.final

class BuilderObject (GObject.GObject):

	ui_file = None
	ui_name = None

	class __Objects (object):
		__slots__ = ["__builder"]
		def __init__ (self, builder):
			self.__builder = builder
		def __getattr__ (self, x):
			ret = self.__builder.get_object (x)
			if ret is None:
				raise AttributeError ("no object %r" % x)
			return ret

	def __new__ (cls, *args, **kwargs):
		builder = Gtk.Builder ()
		builder.add_from_file (os.path.join (UI_LOCATION, cls.ui_file))
		window = builder.get_object (cls.ui_name)
		window.__class__ = cls
		window.objects = cls.__Objects (builder)
		return window

	def __init__ (self):
		pass

class BuilderWindow (BuilderObject, Gtk.Window):
	pass

class BuilderDialog (BuilderObject, Gtk.Dialog):
	pass
