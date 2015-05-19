import re
import collections
import sys
import os
import pickle
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

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
		trained_model[site] = Pipeline([('vect', CountVectorizer()), ('tfdif', TfidfTransformer()), ('clf', MultinomialNB())])
		
		# method1
		# data_list = visit_record[site][0] + visit_record[site][1]
		# target_list = [0 for i in range(click_len)] + [1 for i in range(object_len)]
		
		#method2
		data_list = ['', '']
		for item in visit_record[site][0]:
			data_list[0] = data_list[0] + item
		for item in visit_record[site][1]:
			data_list[1] = data_list[1] + item
		target_list = [0, 1]

		#method3
		trained_model[site].fit(data_list, target_list)

def dump_trained_model():
	for site in trained_model:
		output = open('../trained_model/%s.pkl' % site, 'wb')
		pickle.dump(trained_model[site], output)
		output.close()

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
							if trained_model[site_name].predict([url])[0] == 1:
								predicted_object_number = predicted_object_number + 1
	print 'accuracy: %f, predicted_session_number: %d, session_number: %d' % (1.0 * predicted_session_number / session_number, predicted_session_number, session_number)
	print 'accuracy: %f, predicted_object_number : %d, object_number : %d' % (1.0 * predicted_object_number / object_number, predicted_object_number, object_number)
if __name__ == '__main__':
	read_files_and_process()
	train_classification_model()
	# dump_trained_model()
	basic_test()