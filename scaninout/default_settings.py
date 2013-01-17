expires_cutoff_time = 4

# default password is "password"
password_hash_hex = 'b8792f00bc54588c9ec76225b453fce94994c57efc1f26835110d7d357fa48cb'

def validate_tag (tag):
	if len (tag) != 10:
		return False
	if tag[0:2] != "H0":
		return False
	if not tag[2:].isdigit ():
		return False
	return True
