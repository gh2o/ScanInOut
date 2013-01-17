import hashlib
import hmac
from .pbkdf2 import pbkdf2_bin
from xml.sax.saxutils import escape as escape_xml

SALT = '\xc9\xb5\x04\xe7\x8bEp\x036P\x13~V\xda\xab\x10'
SALT += 'J\x8b\x84\xc4E\xd4\xc0\xcb{\xfb\xb1\xaa\x10\xc2]r'

def generate_pwhash (password):
	return pbkdf2_bin (password, SALT, iterations=1000, keylen=32)

def generate_signature (pwhash, nonce, data):
	h = hmac.new (pwhash, digestmod=hashlib.sha256)
	h.update (nonce)
	h.update (data)
	return h.hexdigest ()
