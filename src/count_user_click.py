import re
import collections
import sys
import os
import pickle
import url_extractor
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

trained_model = {}
top_sites = set()
click_record = {} # key: site, value: list of records
f_anomaly = open('../anomaly/anomaly.txt', 'w')
f_oneclick = open('../anomaly/one_click.txt', 'w')
f_fine = open('../anomaly/fine.txt', 'w')

def read_models():
	path = '../trained_model'
	item_list = os.listdir(path)
	for item in item_list:
		if item.find('.pkl') >= 0:
			site = item.split('.')[0]
			model_file = open('%s/%s' % (path, item), 'r')
			trained_model[site] = pickle.load(model_file)
			model_file.close()
			top_sites.add(site)

def parse_lines(lines):
	regex_sesion = re.compile(r'a new session: (.*)')
	regex_url = re.compile(r'time: (\d*), url: (.*)')

	a_new_session = False
	site_name = None
	Info = None
	visit_list = []
	time_list = []

	

	for line in lines:
		match = re.match(regex_sesion, line)
		if match is not None:
			if len(visit_list) > 0 and (site_name in top_sites):
				if site_name not in click_record:
					click_record[site_name] = []
				try:
					extract_url_list = [url_extractor.extract(full_url) for full_url in visit_list]
					predicted = trained_model[site_name].predict(extract_url_list) # 0 - click, 1 - object
					predicted[0] = 0
					click_number = len(visit_list) - sum(predicted) # length - object
					click_record[site_name].append('click_number: %d, time: %s - %s, Info: %s' % (click_number, time_list[0], time_list[-1], Info))

					# output anomaly
					if click_number >= 10:
						for i in range(len(predicted)):
							if (predicted[i] == 0):
								f_anomaly.write('time: %d, url: %s\n' % (time_list[i], visit_list[i]))
								# print 'time: %d, url: %s\n' % (time_list[i], visit_list[i])
						f_anomaly.write('\n')
					
					elif click_number == 1:
						for i in range(len(predicted)):
							if (predicted[i] == 0):
								f_oneclick.write('time: %d, url: %s\n' % (time_list[i], visit_list[i]))
								# print 'time: %d, url: %s\n' % (time_list[i], visit_list[i])
						f_oneclick.write('\n')
					elif click_number > 1 and click_number < 10:
						for i in range(len(predicted)):
							if (predicted[i] == 0):
								f_fine.write('time: %d, url: %s\n' % (time_list[i], visit_list[i]))
								# print 'time: %d, url: %s\n' % (time_list[i], visit_list[i])
						f_fine.write('\n')
					# There are seesions with session number == 0
				except Exception, e:
					print e

			a_new_session = True
			site_name = None
			Info = match.group(1)
			visit_list = []
			time_list = []
			continue

		match = re.match(regex_url, line)
		if match is not None:
			timestamp = int(match.group(1))
			url = match.group(2)
			if a_new_session:
				a_new_session = False
				domain = url.split('/')[0].split('.')
				for item in domain:
					if item in top_sites:
						site_name = item
						break
			
			time_list.append(timestamp)
			visit_list.append(url)

	

def detect_user_click():
	path = '../parsed_data'
	item_list = os.listdir(path)
	for item in item_list:
		if item.find('.txt') >= 0:
			f = open('%s/%s' % (path, item), 'r')
			lines = f.readlines()
			parse_lines(lines)
			f.close()
	f_anomaly.close()
	f_oneclick.close()
	f_fine.close()

def dump_record():
	path = '../click_record'
	for item in click_record:
		f = open('%s/%s.txt' % (path, item), 'w')
		for line in click_record[item]:
			f.write(line + '\n')
		f.close()

if __name__ == '__main__':
	read_models()
	print trained_model['sina'].predict(['www.sina.com.cn', 'www.sohu.com.cn', 'sina', 'sohu'])
	detect_user_click()
	dump_record()