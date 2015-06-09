# -*- coding: utf-8 -*-
import pickle
import re
import os
import sys
import numpy
from random import shuffle
from scipy import stats
from bisect import bisect
from sklearn import tree
from sklearn.tree import DecisionTreeRegressor
from sklearn.externals.six import StringIO
import matplotlib.pyplot as plt
result_path = '../result'

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
	'acfun',
	'bilibili',
	'zhidao',
}

starttime_list = []

# read click record of a site
def read_records_of_a_site(site_name):
	f = open('../click_record/%s.txt' % site_name, 'r')
	lines = f.readlines()
	f.close()
	return lines

# find the channel data or station data according to start_time and end_time
def find_records(file_name, start_time, end_time, device_MAC, AP_MAC):
	file_path = '../wifidata/%s/%s' % (AP_MAC, file_name)
	f = open(file_path, 'r')
	lines = f.readlines()
	f.close()

	# start_time and end_time are string
	start_index = bisect(lines, start_time)
	end_index = bisect(lines, end_time)
	return lines[start_index - 1 : end_index + 1] # The index may overflow

def compute_cdf(raw_data):
	raw_data.sort()
	X = []
	Y = []
	X.append(raw_data[0])
	Y.append(0)
	for i in range(len(raw_data) - 1):
		if raw_data[i] != raw_data[i+1]:
			X.append(raw_data[i])
			Y.append((i + 1) * 1.0 / len(raw_data))
	X.append(raw_data[-1])
	Y.append(1)
	return X, Y

def mean_confidence_interval(data, confidence=0.95):
    a = 1.0*np.array(data)
    n = len(a)
    m, se = np.mean(a), scipy.stats.sem(a)
    h = se * sp.stats.t._ppf((1+confidence)/2., n-1)
    return m, m-h, m+h

regex_click_record = re.compile(r'click_number: (\d*), time: (\d*) - (\d*), Info: (\w*) len: (\d*) MAC: (.*) AP_MAC: (.*)$')
# find the corresponding wifi data according to a click record line
def get_wireless_record(line):
	match = re.match(regex_click_record, line)
	click_number = 0;
	start_time = 0;
	end_time = 0;
	site = 'N/A';
	visit_length = 0;
	MAC = 'NULL';
	AP_MAC = 'NULL'

	if match is None:
		return None, None

	click_number = match.group(1);
	start_time = match.group(2);
	end_time = match.group(3);
	site = match.group(4);
	visit_length = match.group(5);
	MAC = match.group(6)
	AP_MAC = match.group(7)

	AP_file_path = '../wifidata/%s' % AP_MAC
	if not os.path.isdir(AP_file_path):
		# print 'No such AP'
		# print line
		return None, None
	AP_file_list = os.listdir(AP_file_path)
	# print AP_file_list
	if ('station.txt' not in AP_file_list) or ('channel.txt' not in AP_file_list):
		# print 'No station.txt or channel.txt'
		# print line
		return None, None

	channel_records = find_records('channel.txt', start_time, end_time, MAC, AP_MAC)
	if (len(channel_records) == 0):
		# print 'len(channel_records) == 0'
		# print line
		return None, None
	# channel: timestamp, active, busy, rx_time, tx_time
	channel_start = channel_records[0].split(',')
	channel_end = channel_records[-1].split(',')
	channel_duration = (int)(channel_end[0]) - (int)(channel_start[0])
	if channel_duration == 0:
		# print 'channel_duration == 0'
		# print line
		return None, None
	# channel_active = ((int)(channel_end[1]) - (int)(channel_start[1])) * 1.0 / channel_duration
	channel_busy = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / channel_duration
	channel_rxtime = ((int)(channel_end[3]) - (int)(channel_start[3])) * 1.0 / channel_duration
	channel_txtime = ((int)(channel_end[4]) - (int)(channel_start[4])) * 1.0 / channel_duration
	# channel_air_utilization = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / ((int)(channel_end[1]) - (int)(channel_start[1]))
	channel_air_utilization = (( ((int)(channel_end[2])) - ((int)(channel_end[3])) - ((int)(channel_end[4])) ) - ( ((int)(channel_start[2])) - ((int)(channel_start[3])) - ((int)(channel_start[4])) )) * 1.0 / ((int)(channel_end[1]) - (int)(channel_start[1]))
	if ((channel_busy < 0) or (channel_rxtime < 0) or (channel_txtime < 0)):
		return None, None

	station_records = find_records('station.txt', start_time, end_time, MAC, AP_MAC)
	# station: 0-timestamp, 1-devMAC, 2-receive_byte, 3-send_byte, 4-send_packet, 5-resend_packet, 6-signal, 7-send_phyrate, 8-receive_phyrate
	station_startindex = -1
	station_endindex = -1

	MAC_parts = MAC.split(':')
	NEW_MAC = ''
	# go wrong if more than one part shortened by xx::xx
	for item in MAC_parts:
		if len(item) == 1:
			item = '0' + item
		if len(item) == 0:
			item = '00'
		NEW_MAC = NEW_MAC + item
	DEV_MAC = NEW_MAC.lower()
	# print DEV_MAC
	for i in range(len(station_records)):
		if station_records[i].find(DEV_MAC) >= 0:
			station_startindex = i
	for i in range(len(station_records) - 1, -1, -1):
		if station_records[i].find(DEV_MAC) >= 0:
			station_endindex = i
	
	if station_startindex < 0:
		# print 'No Dev'
		# print line
		return None, None

	# IMPORTANT CONDITON to decide if add duration like station record
	if station_startindex == station_endindex:
		# print 'station_startindex == station_endindex'
		# print line
		return None, None

	station_start = station_records[station_startindex].split(',')
	station_end = station_records[station_endindex].split(',')
	station_duration = ((int)(station_end[0])) - ((int)(station_start[0]))
	station_rxbyte = ((int)(station_end[2]) - (int)(station_start[2])) * 1.0 / station_duration
	station_txbyte = ((int)(station_end[3]) - (int)(station_start[3])) * 1.0 / station_duration
	station_send_packet = ((int)(station_end[4]) - (int)(station_start[4])) * 1.0 / station_duration
	station_resend_packet = ((int)(station_end[5]) - (int)(station_start[5])) * 1.0 / station_duration
	station_resend_ratio = ((int)(station_end[5]) - (int)(station_start[5])) * 1.0 / ((int)(station_end[4]) - (int)(station_start[4]))
	if station_rxbyte < 0:
		return None, None
	if station_txbyte < 0:
		return None, None
	if station_send_packet < 0:
		return None, None
	if station_resend_packet < 0:
		return None, None
	station_record_number = 0
	station_signal_strength = []
	station_send_phyrate = 0
	station_receive_phyrate = 0

	all_dev = set()
	for item in station_records:
		all_dev.add(item.split(',')[1])
		if item.find(DEV_MAC) < 0:
			continue
		tmp_station_record = item.split(',')
		station_record_number = station_record_number + 1
		station_signal_strength.append((int)(tmp_station_record[6]))
		station_send_phyrate = station_send_phyrate + (float)(tmp_station_record[7])
		station_receive_phyrate = station_receive_phyrate + (float)(tmp_station_record[8])

	statition_dev_number = len(all_dev)
	station_signal_strength.sort()
	station_signal_strength = station_signal_strength[len(station_signal_strength) / 2] # find median signal strength

	station_send_phyrate = station_send_phyrate * 1.0 / station_record_number
	station_receive_phyrate = station_receive_phyrate * 1.0 / station_record_number

	rt = []
	feature_names = []
	
	rt.append(channel_busy)
	feature_names.append('channel_busy')

	rt.append(channel_air_utilization)
	feature_names.append('channel_air_utilization')

	rt.append(channel_rxtime)
	feature_names.append('channel_rxtime')

	rt.append(channel_txtime)
	feature_names.append('channel_txtime')

	rt.append(station_rxbyte)
	feature_names.append('station_rxbyte')

	rt.append(station_txbyte)
	feature_names.append('station_txbyte')
	rt.append(station_send_packet)
	feature_names.append('station_send_packet')
	rt.append(station_resend_packet)
	feature_names.append('station_resend_packet')
	rt.append(station_signal_strength)
	feature_names.append('station_signal_strength')

	rt.append(station_send_phyrate)
	feature_names.append('station_send_phyrate')
	rt.append(station_receive_phyrate)
	feature_names.append('station_receive_phyrate')
	rt.append(statition_dev_number)
	feature_names.append('statition_dev_number')
	rt.append(station_resend_ratio)
	feature_names.append('station_resend_ratio')

	return rt, feature_names

def omit_click_number(click_number):
	# if click_number <= 1 or click_number > 20:
	if click_number > 20:
		return True # omit
	else:
		return False # useful

regex_click_number = re.compile(r'click_number: (\d*),')	

def statistic_info(lines, median):
	click_number_list = []
	for line in lines:
		match = re.match(regex_click_number, line)
		if match is None:
			continue
		click_number = (int)(match.group(1))
		if omit_click_number(click_number):
			continue
		click_number_list.append(click_number)
	click_number_list.sort()
	print click_number_list
	# print click_number_list[int(len(click_number_list) * 0.75)]
	# print numpy.mean(click_number_list)
	n_category_0 = 0
	n_category_1 = 0

	key = median
	for item in click_number_list:
		if item <= key:
			n_category_0 = n_category_0 + 1
		else:
			n_category_1 = n_category_1 + 1
	print 'session_legnth <= %d: %f, session_legnth > %d: %f' % (key, n_category_0 * 1.0 / len(click_number_list), key, n_category_1 * 1.0 / len(click_number_list))
	print 'median: %d' % click_number_list[len(click_number_list) / 2]

def process_data(lines, category_name):
	Line_number = 0
	Omit_number = 0
	None_number = 0
	X = []
	y = []
	feature_names = []
	for line in lines:
		match = re.match(regex_click_number, line)
		if match is None:
			continue
		Line_number = Line_number + 1

		click_number = (int)(match.group(1))
		# get rid of unwanted data
		if omit_click_number(click_number):
			Omit_number = Omit_number + 1
			continue
		wifi_data, rt = get_wireless_record(line)	
		if wifi_data is None:
			None_number = None_number + 1
			continue
		if rt is not None: # get_wireless_record may return None, None
			feature_names = rt
		X.append(wifi_data)
		y.append(click_number)
	print 'process data: %s, original_data: %d, omit: %d, none: %d' % (category_name, Line_number, Omit_number, None_number)

	# different procedures to process data
	# plot_confidence_interval(X, y, category_name, feature_names)
	# scatter_plot(X, y, category_name, feature_names)

def regress_data(wifi_data_list, click_number_list, category_name, feature_names):
	X = wifi_data_list
	sorted_click_number_list = sorted(click_number_list)
	median = sorted_click_number_list(len(sorted_click_number_list) / 2)

	y = []
	for item in click_number_list:
		if item <= median:
			y.append(0)
		else:
			y.append(1)

	# clf = DecisionTreeRegressor(max_depth = 3)
	clf = tree.DecisionTreeClassifier(max_depth=None, criterion='entropy', min_samples_leaf=1)
	
	# # validate code
	# combine = zip(X, y)
	# correct_list = []
	# pivot = int(0.9 * len(combine))
	# for i in range(1000):
	# 	answer = []
	# 	shuffle(combine)
	# 	clf.fit([data[0] for data in combine[:pivot]], [data[1] for data in combine[:pivot]])
	# 	predicted = clf.predict([data[0] for data in combine[pivot:]])
	# 	for item in [data[1] for data in combine[pivot:]]:
	# 		if item <= median:
	# 			answer.append(0)
	# 		else:
	# 			answer.append(1)
	# 	rate = numpy.mean(predicted == answer)
	# 	# print rate
	# 	correct_list.append(rate)

	# print 'final avg: %f' % numpy.mean(correct_list)
	# statistic_info(lines, median)
	# print

	clf.fit(X, y)

	# # dump tree modle
	# output = open('%s/%s.pkl' % (result_path, category_name), 'w')
	# pickle.dump(clf, output)
	# output.close()

	# visualize
	with open('%s/%s.dot' % (result_path, category_name), 'w') as f:
		f = tree.export_graphviz(clf, out_file = f, feature_names=feature_names)
	os.system('dot -Tpdf %s/%s.dot -o %s/%s.pdf' % (result_path, category_name, result_path, category_name))
	print 'Original data: %d, Omit data: %d, None data: %d' % (Line_number, Omit_number, None_number)

def bin_data(univariate_x, y, bins):
	# 根据x排序，对y也排序
	combine = zip(univariate_x, y)
	combine.sort(key = lambda t: t[0])
	# bin之后的x对应一个y的列表
	combine = combine[int(len(combine) * 0.05) : int(len(combine) * 0.95)]
	step = (combine[-1][0] - combine[0][0]) * 1.0 / bins
	basket = []
	print combine[-1][0]
	print combine[0][0]
	print step
	print '------------'
	for i in range(bins + 2):
		basket.append([])
	for item in combine:
		index = int((item[0] - combine[0][0]) / step)

		basket[index].append(item[1])
	
	rt_X = []
	rt_Y = []
	for i in range(len(basket)):
		if (len(basket[i]) > 0):
			rt_Y.append(basket[i])
			rt_X.append(combine[0][0] + i * step)
			# rt_X.append(combine[0][0] + (i * 1.0 + 0.5) * step)
	return rt_X, rt_Y

def plot_confidence_interval(wifi_data_list, click_number_list, category_name, feature_names):
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])

	for i in range(para_number):
		rt_X, rt_Y = bin_data(para_record[i], click_number_list, 10)

		for j in range(len(rt_X)):
			for item in rt_Y[j]:
				plt.scatter(rt_X[j], item)
		plt.savefig('../figure/confident_interval_%s_%s.pdf' % (category_name, feature_names[i]))
		plt.clf()

# f_corrceof = open('%s/corrcoef.txt' % result_path, 'w')
def compute_pearson_correlation(wifi_data_list, click_number_list, category_name, feature_names):
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])
	
	corrcoef_list = []
	result = ''

	for i in range(para_number):
		coef = stats.pearsonr(para_record[i], y)
		corrcoef_list.append(coef)
		result = result + '\t' + (str)(coef[0])
		# print feature_names[i]
	return corrcoef_list
	# f_corrceof.write('%s\n' % category_name)
	# f_corrceof.write('%s\n' % result)

def scatter_plot(wifi_data_list, click_number_list, category_name, feature_names):
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])
	os.system('mkdir ../figure/%s' % category_name)
	for i in range(para_number):
		
		# tmp = zip(para_record[i], click_number_list)
		# tmp.sort(key = lambda t: t[0])
		# s_index = int(len(tmp) * 0.05)
		# t_index = int(len(tmp) * 0.95)
		# tmp = tmp[s_index : t_index]
		# plt.scatter([data[0] for data in tmp], [data[1] for data in tmp])
		plt.scatter(para_record[i], click_number_list)
		plt.savefig('../figure/%s/%s_%s.pdf' % (category_name, category_name, feature_names[i]))
		plt.clf()

def aggregate_records():
	portal_lines = []
	portal_lines = portal_lines + read_records_of_a_site('sina')
	portal_lines = portal_lines + read_records_of_a_site('163')
	portal_lines = portal_lines + read_records_of_a_site('qq')

	video_lines = []
	video_lines = video_lines + read_records_of_a_site('bilibili')
	video_lines = video_lines + read_records_of_a_site('acfun')
	video_lines = video_lines + read_records_of_a_site('tudou')
	video_lines = video_lines + read_records_of_a_site('youku')

	shop_lines = []
	shop_lines = shop_lines + read_records_of_a_site('amazon')
	shop_lines = shop_lines + read_records_of_a_site('taobao')
	shop_lines = shop_lines + read_records_of_a_site('tmall')
	shop_lines = shop_lines + read_records_of_a_site('jd')
	regress_data(shop_lines, 'shop')

	social_lines = []
	social_lines = social_lines + read_records_of_a_site('weibo')
	social_lines = social_lines + read_records_of_a_site('zhihu')
	regress_data(social_lines, 'social')


def traverse_analyze():
	for site in top_sites:
		site_lines = read_records_of_a_site(site)


if __name__ == '__main__':
	site_lines = []
	for site in top_sites:
		site_lines = site_lines + read_records_of_a_site(site)
	process_data(site_lines, 'all')

	# f_corrceof.close()