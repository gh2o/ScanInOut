expires_cutoff_time = 4

def validate_tag (tag):
	if len (tag) != 10:
		return False
	if tag[0:2] != "H0":
		return False
	if not tag[2:].isdigit ():
		return False
	return True
