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

top_sites = {
	'taobao', #2
	'qq', #3
	'sina', #4
	'weibo', #5
	'tmall', #6
	'amazon', #11
	'163', #17
	'jd', #19
	'youku', #20
	'tudou', #25
	'zhihu',
	'youdao',
	'wikipedia',
	'acfun',
	'bilibili',
	'zhidao',
}

visit_record = {} #visit_record = {site_name:[ [click_list], [object_list] ]}
trained_model = {}

def parse_lines(lines):
	regex_sesion = re.compile(r'a new session')
	regex_url = re.compile(r'time: (\d*), url: (.*)')

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
			url = match.group(2)

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


def read_files_and_process():
	path = '../parsed_data'
	item_list = os.listdir(path)
	for item in item_list:
		if item.find('.txt') >= 0:
			f = open('%s/%s' % (path, item), 'r')
			lines = f.readlines()
			parse_lines(lines)
			f.close()

def train_classification_model():
	for site in visit_record:
		click_len = len(visit_record[site][0])
		object_len = len(visit_record[site][1])
		if click_len == 0 or object_len == 0:
			continue
		# trained_model[site] = Pipeline([('vect', CountVectorizer()), ('tfdif', TfidfTransformer()), ('clf', MultinomialNB())])
		trained_model[site] = Pipeline([('vect', CountVectorizer(stop_words=['www', 'com', 'cn'])), ('clf', MultinomialNB(alpha=0.0001))])
		
		# method1
		# data_list = visit_record[site][0] + visit_record[site][1]
		# click_list = [url_extractor.extract(full_url) for full_url in visit_record[site][0]]
		# click_list = list(set(click_list))
		# object_list = [url_extractor.extract(full_url) for full_url in visit_record[site][1]]
		# object_list = list(set(object_list))
		# data_list = click_list + object_list
		# target_list = [0 for i in range(len(click_list))] + [1 for i in range(len(object_list))]
		# print 'len_click: %d, len_object: %d\n' % (len(click_list), len(object_list))
		# for item in object_list:
		# 	print item

		#method2
		# data_list = ['', '']
		# for item in visit_record[site][0]:
		# 	data_list[0] = data_list[0] + ',' + url_extractor.extract(item)
		# for item in visit_record[site][1]:
		# 	data_list[1] = data_list[1] + ',' + url_extractor.extract(item)
		# target_list = [0, 1]

		#method3
		# tmp_data_list = [[], []]
		# for item in visit_record[site][0]:
		# 	tmp_data_list[0].extend(re.findall(r'[\w]+', url_extractor.extract(item)))
		# for item in visit_record[site][1]:
		# 	tmp_data_list[1].extend(re.findall(r'[\w]+', url_extractor.extract(item)))
		# tmp_data_list[0] = list(set(tmp_data_list[0]))
		# tmp_data_list[1] = list(set(tmp_data_list[1]))
		# data_list = ['', '']
		# for item in tmp_data_list[0]:
		# 	data_list[0] = data_list[0] + item + ','
		# for item in tmp_data_list[1]:
		# 	data_list[1] = data_list[1] + item + ','
		# target_list = [0, 1]

		#method4
		tmp_data_list = [[], []]
		for item in visit_record[site][0]:
			tmp_data_list[0].extend(re.findall(r'[\w]+', url_extractor.extract(item)))
		for item in visit_record[site][1]:
			tmp_data_list[1].extend(re.findall(r'[\w]+', url_extractor.extract(item)))
		tmp_data_list[0] = list(set(tmp_data_list[0]))
		tmp_data_list[1] = list(set(tmp_data_list[1]))
		
		data_list = tmp_data_list[0] + tmp_data_list[1]
		target_list = [0 for i in range(len(tmp_data_list[0]))] + [1 for i in range(len(tmp_data_list[1]))]
		
		# print 'len_click: %d, len_object: %d\n' % (len(tmp_data_list[0]), len(tmp_data_list[1]))
		# print tmp_data_list[0]
		# print tmp_data_list[1]
		# try:
		trained_model[site].fit(data_list, target_list)
		# except Exception, e:
			# print site


def dump_trained_model():
	for site in trained_model:
		output = open('../trained_model/%s.pkl' % site, 'wb')
		pickle.dump(trained_model[site], output)
		output.close()

# Only consider the first request of a session as a user click
# Do not have the 10s time limit
def basic_test():
	path = '../parsed_data'
	item_list = os.listdir(path)
	session_number = 0
	predicted_session_number = 0
	object_number = 0
	predicted_object_number = 0

	for item in item_list:
		if item.find('.txt') >= 0:
			f = open('%s/%s' % (path, item), 'r')
			lines = f.readlines()
			f.close()

			regex_sesion = re.compile(r'a new session')
			regex_url = re.compile(r'time: (\d*), url: (.*)')
			site_name = None
			a_new_session = False
			for line in lines:
				match = re.match(regex_sesion, line)
				if match is not None:
					a_new_session = True
					site_name = None
					continue

				match = re.match(regex_url, line)
				if match is not None:
					url = match.group(2)

					if a_new_session:
						a_new_session = False

						domain = url.split('/')[0].split('.')
						for item in domain:
							if item in trained_model:
								site_name = item
								session_number = session_number + 1
								if trained_model[item].predict([url])[0] == 0:
									predicted_session_number = predicted_session_number + 1
								break
					else:
						if site_name is not None:
							object_number = object_number + 1
							# if trained_model[site_name].predict([url])[0] == 1:
								# predicted_object_number = predicted_object_number + 1

							try:
								if trained_model[site_name].predict([url])[0] == 1:
									predicted_object_number = predicted_object_number + 1
							except Exception, e:
								print e
								print url
								print item
							
	print 'accuracy: %f, predicted_session_number: %d, session_number: %d' % (1.0 * predicted_session_number / session_number, predicted_session_number, session_number)
	print 'accuracy: %f, predicted_object_number : %d, object_number : %d' % (1.0 * predicted_object_number / object_number, predicted_object_number, object_number)

if __name__ == '__main__':
	read_files_and_process()
	train_classification_model()
	dump_trained_model()
	# basic_test()