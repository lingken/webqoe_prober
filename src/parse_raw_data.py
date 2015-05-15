import re
def is_valid_user_agent(user_agent):
	string = user_agent.lower()
	if string.find('chrome') >= 0:
		return True
	if string.find('firefox') >= 0:
		return True
	if string.find('firefox') >= 0:
		return True;
	if string.find('ie') >= 0:
		return True
	return False

class Session:
	def __init__(self):
		self.url_list = []
		self.timestamp_list = []

record_dict = {}
session_list = []
# c_miss = 0
def parse_lines(lines):
	regex_record = re.compile(r'time: (\d*) \+ (\d*), MAC src: (.*), GET: (.*), Host: (.*), User-Agent: (.*), Referer: (.*)')
	# for line in lines:
	for line in lines:
		match = re.match(regex_record, line)
		if match is None:
			continue
		timestamp = match.group(1)
		MAC = match.group(3)
		GET = match.group(4)
		Host = match.group(5)
		User_Agent = match.group(6)
		Referer = match.group(7)

		if not is_valid_user_agent(User_Agent):
			continue

		# print timestamp
		# print MAC
		# print GET
		# print Host
		# print User_Agent
		# print Referer
		# print

		if MAC not in record_dict:
			record_dict[MAC] = {}
		if User_Agent not in record_dict[MAC]:
			record_dict[MAC][User_Agent] = {}
		if Referer == 'NULL': # a new session
			session = Session()
			new_ref = Host + GET
			session.url_list.append(new_ref)
			session.timestamp_list.append(timestamp)
			session_list.append(session)
			record_dict[MAC][User_Agent][new_ref] = session
		else:
			ref = Referer[7:]
			if ref not in record_dict[MAC][User_Agent]:
				# c_miss = c_miss + 1
				continue
			session = record_dict[MAC][User_Agent][ref]
			new_ref = Host + GET
			session.url_list.append(new_ref)
			session.timestamp_list.append(timestamp)
			record_dict[MAC][User_Agent][new_ref] = session
		# print session_list

def print_all_record():
	for session in session_list:
		print 'a new session:'
		for timestamp, url in zip(session.timestamp_list, session.url_list):
			print 'time: %s, url: %s' % (timestamp, url)
		print

if __name__ == "__main__":
	f = open('trace.txt', 'r')
	lines = f.readlines()
	f.close()
	parse_lines(lines)
	print_all_record()