import re
import collections
import sys
import os
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

trained_model = {}
top_sites = set()
click_record = {} # key: site, value: list of records

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
	MAC = None
	visit_list = []
	time_list = []

	for line in lines:
		match = re.match(regex_sesion, line)
		if match is not None:
			if len(visit_list) > 0 and (site_name in top_sites):
				if site_name not in click_record:
					click_record[site_name] = []
				try:
					click_number = len(visit_list) - sum(trained_model[site_name].predict(visit_list))
					click_record[site_name].append('click_number: %d, time: %s - %s, MAC: %s' % (click_number, time_list[0], time_list[-1], MAC))
				except Exception, e:
					print e
			a_new_session = True
			site_name = None
			MAC = match.group(1)
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

def dump_record():
	path = '../click_record'
	for item in click_record:
		f = open('%s/%s.txt' % (path, item), 'w')
		for line in click_record[item]:
			f.write(line + '\n')
		f.close()

if __name__ == '__main__':
	read_models()
	detect_user_click()
	dump_record()