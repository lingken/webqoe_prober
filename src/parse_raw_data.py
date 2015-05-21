import re
import collections
import sys
import os
import pickle
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
		self.MAC = 'NULL'

def parse_lines(lines, record_dict, session_list):
	# c_miss = 0
	regex_record = re.compile(r'time: (\d*) \+ (\d*), MAC src: (.*), GET: (.*), Host: (.*), User-Agent: (.*), Referer: (.*)')
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
			session.MAC = MAC
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

def print_all_record():
	for session in session_list:
		print 'a new session:'
		for timestamp, url in zip(session.timestamp_list, session.url_list):
			print 'time: %s, url: %s' % (timestamp, url)
		print

def write_session_record(session_list, router, file_time):
	if len(session_list) == 0:
		return
	file_name = '../parsed_data/%s_%d.txt' % (router, file_time)
	f_out = open(file_name, 'w')
	for session in session_list:
		f_out.write('a new session: %s\n' % session.MAC)
		for timestamp, url in zip(session.timestamp_list, session.url_list):
			f_out.write('time: %s, url: %s\n' % (timestamp, url))
		f_out.write('\n')
	f_out.close()

# 1431550800, 2015.5.14 05:00, Beijing time, 1 day - 86400s
def read_files():
	path = '../webqoe_data'
	router_list = os.listdir(path)
	for router in router_list:
		new_path = path + '/' + router
		if not os.path.isdir(new_path):
			continue
		file_list = os.listdir(new_path)
		start_time = 1431550800
		interval = 86400
		record_dict = {}
		session_list = []
		file_list.sort()
		print file_list
		for item in file_list:
			if item.find('.txt') < 0:
				continue
			file_time = int(item.split('.')[0])
			if file_time > start_time + interval:
				write_session_record(session_list, router, start_time)
				# start_time = start_time + interval
				start_time = start_time + ((file_time - start_time) / interval) * interval
				record_dict = {}
				session_list = []
			f = open('%s/%s' % (new_path, item), 'r')
			lines = f.readlines()
			f.close()
			parse_lines(lines, record_dict, session_list)
		write_session_record(session_list, router, file_time)

if __name__ == "__main__":
	read_files()