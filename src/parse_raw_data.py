import re
import collections
import sys
import os
import pickle

top_sites = {
	'taobao', #2
	'qq', #3
	'sina', #4
	'weibo', #5
	'tmall', #6
	'amazon', #11
	'163', #17
	# 'chinadaily', #18
	'jd', #19
	'youku', #20
	# 'alipay', #21
	# 'google', #22
	# 'china', #23
	# 'sogou', #24
	'tudou', #25

	# 'letv', always session = 1
	'zhihu',
	# 'aliyun',
	# 'apple',
	# 'tsinghua',
	'youdao',
	'wikipedia',
	'acfun',
	'bilibili',
	'zhidao',
	# 'kankan',
	# 'ijinshan',
	# 'qidian'
}
# each session has its visit list
site_session_dict = {}
# calculate the domain name keywords of new sessions
domain_keyword_dict = {}

def is_valid_user_agent(user_agent):
	string = user_agent.lower()
	if string.find('chrome') >= 0:
		return True
	if string.find('firefox') >= 0:
		return True
	if string.find('safari') >= 0:
		return True;
	if string.find('ie') >= 0:
		return True
	return False

class Session:
	def __init__(self):
		self.url_list = []
		self.timestamp_list = []
		self.MAC = 'NULL'
		self.site = 'N/A'

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

			domain = new_ref.split('/')[0].split('.')
			for item in domain:
				if item in top_sites:
					session.site = item
					break

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
		print 'a new session: %s MAC: %s' % (session.site, session.MAC)
		for timestamp, url in zip(session.timestamp_list, session.url_list):
			print 'time: %s, url: %s' % (timestamp, url)
		print

regex_end_url = re.compile(r'.*\.(.{1,5})$')
invalid_type_dict = {
	'css',
	'js',
	'php',
	'jpg',
	'gif',
	'png',
	'svg',
	'ico',
}
# for this site, only url in this filter can it pass
absolute_filter = {
	'qq' : {'www.qq.com/', 'qzone.qq.com/', },

}
# for this site, if a url domain contains these words, it cannot be passed
negative_filter = {
	'163' : {'fs-', 'count', 'money', 'music', }, # money, music are useful url, however they are always session = 1
	'sina': {'login', 'video', 'comment', 'dpool', 'js', },
	'qq'  : {'dns', 'html5', 'short', },
	# 'taobao': {'simba', 'svcstatus', 'm.taobao', 'err.', 'ip.taobao', 'ald.taobao', 'tui.taobao', 'allot-map', 'count.taobao', 'suggest.taobao', 'shoucang.taobao'},
}
# positive_filter = {
# 	'taobao': 
# }
def pass_filter(site, url):
	# decide if a url is the beginning of a session
	match = re.match(regex_end_url, url)
	if match is not None:
		url_type = match.group(1)
		if url_type in invalid_type_dict:
			return False
	if site in negative_filter:
		for item in negative_filter[site]:
			if url.find(item) >= 0:
				return False
	if site in absolute_filter:
		if url in absolute_filter[site]:
			return True
		else:
			return False
	return True

def write_session_record(session_list, router, file_time):
	if len(session_list) == 0:
		return
	file_name = '../parsed_data/%s_%d.txt' % (router, file_time)
	f_out = open(file_name, 'w')
	for session in session_list:
		# DANGER:
		if len(session.url_list) == 1:
			continue
		# write out session here; I can separate different websites here
		# generate session records by site
		begin_url = session.url_list[0]
		domain = begin_url.split('/')[0].split('.')
		site = session.site

		# calculate the keywords appeared in domain name
		for keyword in domain:
			if keyword not in domain_keyword_dict:
				domain_keyword_dict[keyword] = 0
			domain_keyword_dict[keyword] = domain_keyword_dict[keyword] + 1

		# for item in domain:
		# 	if item in top_sites:
		# 		site = item
		# 		break;
		# categorize sessions by site
		# if site is not None:
		if site != 'N/A':
			# use the filter to process sites that belong to top_sites
			if not pass_filter(site, begin_url):
				continue

			if site not in site_session_dict:
				site_session_dict[site] = []
			site_session_dict[site].append(session)

		# add a filter here to remove obvious invalid url
		f_out.write('a new session: %s len: %d MAC: %s\n' % (session.site, len(session.url_list), session.MAC))
		for timestamp, url in zip(session.timestamp_list, session.url_list):
			f_out.write('time: %s, url: %s\n' % (timestamp, url))
		f_out.write('\n')
	f_out.close()

def write_visit_by_site():
	print 'write_by_site'
	for site in site_session_dict:
		print site
		f_out = open('../visit_by_site/%s.txt' % site, 'w')
		for session in site_session_dict[site]:


			# DANGER:
			# if len(session.url_list) == 1:
			# 	continue

			f_out.write('a new session: %s len: %d MAC: %s\n' % (session.site, len(session.url_list), session.MAC))
			for timestamp, url in zip(session.timestamp_list, session.url_list):
				f_out.write('time: %s, url: %s\n' % (timestamp, url))
			f_out.write('\n')
		f_out.close()	

# 1431550800, 2015.5.14 05:00, Beijing time, 1 day - 86400s
def read_files():
	path = '../webqoe_data'
	router_list = os.listdir(path)
	for router in router_list:
		print 'Begin router: %s' % router
		new_path = path + '/' + router
		if not os.path.isdir(new_path):
			continue
		file_list = os.listdir(new_path)
		start_time = 1431550800
		interval = 86400
		record_dict = {}
		# record_dict {PC/phone_MAC -> Useragent -> Ref -> Session}

		session_list = []
		file_list.sort()
		# print file_list
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

def write_domain_keyword():
	f = open('domain_keywords.txt', 'w')
	for key, value in sorted(domain_keyword_dict.iteritems(), key=lambda (k,v): (v,k)):
    	# print "%s: %s" % (key, value)
		f.write('%s: %d\n'% (key, value))
	f.close()

if __name__ == "__main__":
	read_files()
	write_visit_by_site()
	write_domain_keyword()
