import re
def extract(url):
	# return url.split('/')[0]
	# make a bag of words separated by '.'
	# reserve three parts of domain and the file type
	parts = url.split('/')
	rt = ''
	parts_number = 3
	if (len(parts) > parts_number):
		for i in range(parts_number):
			rt = rt + parts[i] + '.'
	else:
		for i in range(len(parts) - 1):
			rt = rt + parts[i] + '.'

	regex_end_url = re.compile(r'.*/.*\.(.{1,5})$')
	match = re.match(regex_end_url, url)
	if match is not None:
		rt = rt + match.group(1)
	return rt

	# return url