# expected input
#   data: [url1, url2, url3, ...]
# target: [   0,    1,    1, ...] 0 - user click, 1 - embedded objects

# Label user click and embedded objects automatically
import re
import collections
import sys
import os
import pickle
top_sites = {
	'baidu:1', #1
	'taobao', #2
	'qq', #3
	'sina', #4
	'weibo', #5
	'tmall', #6
	'hao123', #7
	'sohu', #8
	'360', #9
	'tianya', #10
	'amazon', #11
	'xinhuanet', #12
	'people', #13
	'cntv', #14
	'gmw', #15
	'soso', #16
	'163', #17
	'chinadaily', #18
	'jd', #19
	'youku', #20
	'alipay', #21
	'google', #22
	'china', #23
	'sogou', #24
	'tudou', #25
	# 'youdao',
	# '3dmgame'
}

visit_record = {} #visit_record = {site_name:[ [click_list], [object_list] ]}
word_record = {}
probability_record = {}

# import sys
# import os

# path = sys.path[0]
# item_list = os.listdir(path)

# i = 0
# for item in item_list:
# 	if item.find('pcap') >= 0:
# 		print "begin: " + item
# 		os.system("./simple_sniffer_file %s" % item)

def read_files_and_process():
	path = '../record'
	item_list = os.listdir(path)
	for item in item_list:
		if item.find('pcap') >= 0:
			f = open('%s/%s' % (path, item), 'r')
			lines = f.readlines()
			# process the file
			parse_lines(lines)
			f.close()

def parse_lines(lines):
	regex_sesion = re.compile(r'a new session')
	regex_url = re.compile(r'time: (\d*) \+ (\d*), url: (.*)')

	initial_time = -1
	a_new_session = False
	site_name = None
	for line in lines:
		match = re.match(regex_sesion, line)
		if match is not None:
			a_new_session = True
			site_name = None
			continue

		match = re.match(regex_url, line)
		if match is not None:
			timestamp = int(match.group(1))
			url = match.group(3)

			if a_new_session:
				initial_time = timestamp
				a_new_session = False

				domain = url.split('/')[0].split('.')
				for item in domain:
					if item in top_sites:
						site_name = item
						break
				if site_name is not None:
					if site_name not in visit_record:
						visit_record[site_name] = [[], []]
					visit_record[site_name][0].append(url)
			else:
				if (site_name is not None) and (timestamp - initial_time <= 10):
					visit_record[site_name][1].append(url)

def calc_probability(word_list):
	unique_word_number = 0
	total_word_number = 0
	word_dict = {}
	for word in word_list:
		total_word_number = total_word_number + 1
		if word in word_dict:
			word_dict[word] = word_dict[word] + 1
		else:
			word_dict[word] = 1
			unique_word_number = unique_word_number + 1
	# Laplace Smoothing for Naive Bayes
	for item in word_dict:
		word_dict[item] = (word_dict[item] + 1) * 1.0 / (total_word_number + unique_word_number)
	p_not_exist = 1.0 / (total_word_number + unique_word_number)
	return p_not_exist, word_dict

def dissect_url_into_words():
	for site_name in visit_record:
		word_record[site_name] = [[], []]
		for click_url in visit_record[site_name][0]:
			word_record[site_name][0].extend(re.findall(r'[\w]+', click_url))

		for object_url in visit_record[site_name][1]:
			word_record[site_name][1].extend(re.findall(r'[\w]+', object_url))	

def process_and_write_to_file():
	for site_name in word_record:
		p_category_click = 1.0 * len(visit_record[site_name][0]) / (len(visit_record[site_name][0]) + len(visit_record[site_name][1]))
		p_category_object = 1.0 * len(visit_record[site_name][1]) / (len(visit_record[site_name][0]) + len(visit_record[site_name][1]))
		probability_record[site_name] = [[], []]
		p_not_exist_click, probability_record[site_name][0] = calc_probability(word_record[site_name][0])
		p_not_exist_object, probability_record[site_name][1] = calc_probability(word_record[site_name][1])

		f_click = open('../format_data/%s_click.txt' % site_name, 'w')
		f_click.write('%s click\n' % site_name)
		f_click.write('%f %f\n' % (p_category_click, p_not_exist_click))
		for word in probability_record[site_name][0]:
			f_click.write('%s %f\n' % (word, probability_record[site_name][0][word]))
		f_click.close()

		f_object = open('../format_data/%s_object.txt' % site_name, 'w')
		f_object.write('%s object\n' % site_name)
		f_object.write('%f %f\n' % (p_category_object, p_not_exist_object))
		for word in probability_record[site_name][1]:
			f_object.write('%s %f\n' % (word, probability_record[site_name][1][word]))
		f_object.close()

if __name__ == "__main__":
	# read_files_and_process()
	# output = open('visit_record.pkl', 'wb')
	# pickle.dump(visit_record, output)
	# output.close()

	pkl_file = open('visit_record.pkl', 'rb')
	visit_record = pickle.load(pkl_file)
	for item in visit_record['sina'][0]:
		print item
	pkl_file.close()
	# parse_lines(lines)
	# dissect_url_into_words()
	# process_and_write_to_file()

