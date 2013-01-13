DEFAULT_SOCKET_PATH = "/tmp/scaninout"

def init ():

	class Settings (object):
		def configure (self, path):
			exec open (path).read () in self.__dict__
	
	from os import path as p
	d = p.join (p.dirname (p.realpath (__file__)), "default_settings.py")

	global settings
	settings = Settings ()
	settings.configure (d)

init ()
del init
