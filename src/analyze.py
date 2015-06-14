# -*- coding: utf-8 -*-
import pickle
import re
import os
import sys
import numpy
from random import shuffle
from scipy import stats
from sklearn import metrics
from bisect import bisect

from sklearn import tree
# from sklearn.tree import DecisionTreeRegressor
from sklearn import cross_validation
# from sklearn import svm

import matplotlib.pyplot as plt
result_path = '../result'

top_sites = {
	'taobao', #2
	# 'qq', #3
	'sina', #4
	'weibo', #5
	# 'tmall', #6
	# 'amazon', #11
	'163', #17
	'jd', #19
	'youku', #20
	'tudou', #25
	'zhihu',
	'youdao',
	'acfun',
	'bilibili',
	# 'zhidao',
}

feature_names = [
	# 'delay',
	'session_duration',
	# 'channel_active',
	# 'channel_busy',
	'channel_air_utilization',
	# 'channel_rxtime',
	# 'channel_txtime', # additional
	# 'station_rxbyte',
	# 'station_txbyte',
	# 'station_send_packet', # additional
	'station_resend_packet',
	'station_signal_strength',
	# 'station_send_phyrate',
	'station_receive_phyrate',
	# 'statition_dev_number',
	# 'station_resend_ratio',
]
feature_dict = {}

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
	end_time = str(int(end_time) + 1)
	end_index = bisect(lines, end_time)
	return lines[start_index - 1 : end_index + 1] # The index may overflow

def find_delay_records(start_time, end_time, AP_MAC):
	file_path = '../delay_use/%s/delay.txt' % AP_MAC
	f = open(file_path, 'r')
	lines = f.readlines()
	f.close()

	# start_time and end_time are string
	start_index = bisect(lines, start_time)
	end_time = str(int(end_time) + 1)
	end_index = bisect(lines, end_time)
	return lines[start_index - 1 : end_index + 1]

# def compute_cdf(raw_data):
# 	raw_data.sort()
# 	X = []
# 	Y = []
# 	X.append(raw_data[0])
# 	Y.append(0)
# 	for i in range(len(raw_data) - 1):
# 		if raw_data[i] != raw_data[i+1]:
# 			X.append(raw_data[i])
# 			Y.append((i + 1) * 1.0 / len(raw_data))
# 	X.append(raw_data[-1])
# 	Y.append(1)
# 	return X, Y

def compute_cdf(raw_data):
	raw_data.sort()
	X = []
	Y = []
	X.append(raw_data[0])
	Y.append(0)
	last = 0
	for i in range(len(raw_data) - 1):
		if raw_data[i] != raw_data[i+1]:
			X.append(raw_data[i])
			Y.append(last)
			X.append(raw_data[i])
			last = (i + 1) * 1.0 / len(raw_data)
			Y.append(last)
	X.append(raw_data[-1])
	Y.append(last)
	X.append(raw_data[-1])
	Y.append(1)
	return X, Y

def mean_confidence_interval(data, confidence=0.95):
    a = 1.0*numpy.array(data)
    n = len(a)
    m, se = numpy.mean(a), stats.sem(a)
    h = se * stats.t._ppf((1+confidence)/2., n-1)
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
		return None

	click_number = match.group(1);
	start_time = match.group(2);
	end_time = match.group(3);
	site = match.group(4);
	visit_length = match.group(5);
	MAC = match.group(6)
	AP_MAC = match.group(7)
	
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

	if not os.path.exists('../wifidata/%s/channel.txt' % AP_MAC):
		return None
	if not os.path.exists('../wifidata/%s/station.txt' % AP_MAC):
		return None
	if not os.path.exists('../delay_use/%s/delay.txt' % AP_MAC):
		return None


	session_duration = int(end_time) - int(start_time)

	# if session_duration > 360:
		# return None

	delay_time = 0
	# delay_records = find_delay_records(start_time, end_time, AP_MAC)
	# if (len(delay_records) == 0):
	# 	return None
	# # ack_count = 0
	# # data_count = 0
	# delay_count = 0
	# for item in delay_records:
	# 	# if item.find(DEV_MAC) < 0:
	# 		# continue
	# 	delay_parts = item.split(',')
	# 	time1 = float(delay_parts[0])
	# 	time3 = float(delay_parts[2])
	# 	delay_count = delay_count + 1
	# 	delay_time = delay_time + (time3 - time1)
	# if delay_count == 0:
	# 	return None
	# delay_time = delay_time / delay_count





	channel_records = find_records('channel.txt', start_time, end_time, MAC, AP_MAC)
	if (len(channel_records) == 0):
		# print 'len(channel_records) == 0'
		# print line
		return None
	# channel: timestamp, active, busy, rx_time, tx_time
	channel_start = channel_records[0].split(',')
	channel_end = channel_records[-1].split(',')
	channel_duration = (int)(channel_end[0]) - (int)(channel_start[0])
	if channel_duration == 0:
		# print 'channel_duration == 0'
		# print line
		return None
	channel_active = ((int)(channel_end[1]) - (int)(channel_start[1]))
	channel_busy = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / channel_active
	channel_rxtime = ((int)(channel_end[3]) - (int)(channel_start[3])) * 1.0 / channel_active
	channel_txtime = ((int)(channel_end[4]) - (int)(channel_start[4])) * 1.0 / channel_active
	# channel_air_utilization = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / ((int)(channel_end[1]) - (int)(channel_start[1]))
	channel_air_utilization = (( ((int)(channel_end[2])) - ((int)(channel_end[3])) - ((int)(channel_end[4])) ) - ( ((int)(channel_start[2])) - ((int)(channel_start[3])) - ((int)(channel_start[4])) )) * 1.0 / ((int)(channel_end[1]) - (int)(channel_start[1]))
	if ((channel_busy < 0) or (channel_rxtime < 0) or (channel_txtime < 0)):
		return None

	station_records = find_records('station.txt', start_time, end_time, MAC, AP_MAC)
	# station: 0-timestamp, 1-devMAC, 2-receive_byte, 3-send_byte, 4-send_packet, 5-resend_packet, 6-signal, 7-send_phyrate, 8-receive_phyrate
	station_startindex = -1
	station_endindex = -1

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
		return None

	# IMPORTANT CONDITON to decide if add duration like station record
	if station_startindex == station_endindex:
		# print 'station_startindex == station_endindex'
		# print line
		return None

	station_start = station_records[station_startindex].split(',')
	station_end = station_records[station_endindex].split(',')
	station_duration = ((int)(station_end[0])) - ((int)(station_start[0]))
	station_rxbyte = ((int)(station_end[2]) - (int)(station_start[2])) * 1.0 / station_duration
	station_txbyte = ((int)(station_end[3]) - (int)(station_start[3])) * 1.0 / station_duration
	station_send_packet = ((int)(station_end[4]) - (int)(station_start[4])) * 1.0 / station_duration
	station_resend_packet = ((int)(station_end[5]) - (int)(station_start[5])) * 1.0 / station_duration
	station_resend_ratio = ((int)(station_end[5]) - (int)(station_start[5])) * 1.0 / ((int)(station_end[4]) - (int)(station_start[4]))
	if station_rxbyte < 0:
		return None
	if station_txbyte < 0:
		return None
	if station_send_packet < 0:
		return None
	if station_resend_packet < 0:
		return None
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
	if 'delay' in feature_dict:
		rt.append(delay_time)
	if 'session_duration' in feature_dict:
		rt.append(session_duration)
	if 'channel_active' in feature_dict:
		rt.append(channel_active)
	if 'channel_busy' in feature_dict:
		rt.append(channel_busy)
	if 'channel_air_utilization' in feature_dict:
		rt.append(channel_air_utilization)
	if 'channel_rxtime' in feature_dict:
		rt.append(channel_rxtime)
	if 'channel_txtime' in feature_dict:
		rt.append(channel_txtime)
	if 'station_rxbyte' in feature_dict:
		rt.append(station_rxbyte)
	if 'station_txbyte' in feature_dict:
		rt.append(station_txbyte)
	if 'station_send_packet' in feature_dict:
		rt.append(station_send_packet)
	if 'station_resend_packet' in feature_dict:
		rt.append(station_resend_packet)
	if 'station_signal_strength' in feature_dict:
		rt.append(station_signal_strength)
	if 'station_send_phyrate' in feature_dict:
		rt.append(station_send_phyrate)
	if 'station_receive_phyrate' in feature_dict:
		rt.append(station_receive_phyrate)
	if 'statition_dev_number' in feature_dict:
		rt.append(statition_dev_number)
	if 'station_resend_ratio' in feature_dict:
		rt.append(station_resend_ratio)

	return rt

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

def coordinates_to_file(X_data, Y_data, file_name):
	f = open(file_name, 'w')
	for item in X_data:
		f.write('%s, ' % item)
	f.write('\n')
	for item in Y_data:
		f.write('%s, ' % item)
	f.write('\n')
	f.close()

kendall_record = []
info_gain_record = []
def process_data(lines, category_name):
	Line_number = 0
	Omit_number = 0
	None_number = 0
	X = []
	y = []

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
		wifi_data = get_wireless_record(line)	
		if wifi_data is None:
			None_number = None_number + 1
			continue
		X.append(wifi_data)
		y.append(click_number)
	Valid_number = Line_number - Omit_number - None_number
	print 'process data: %s, valid_data: %d, original_data: %d, omit: %d, none: %d' % (category_name, Valid_number, Line_number, Omit_number, None_number)

	# different procedures to process data
	regress_data(X, y, category_name)

	# plot_confidence_interval(X, y, category_name)
	# plot_p25_p75(X, y, category_name)
	# scatter_plot(X, y, category_name)

	# kendall_result = compute_kendall_correlation(X, y, category_name)
	# kendall_record.append([kendall_result, Valid_number])
	
	# info_gain_result = compute_relative_information_gain(X, y, category_name)
	# info_gain_record.append([info_gain_result, Valid_number])
	


def regress_data(wifi_data_list, click_number_list, category_name):
	print 'regression: %s' % category_name
	X = wifi_data_list
	sorted_click_number_list = sorted(click_number_list)
	median = sorted_click_number_list[len(sorted_click_number_list) / 2]

	n_category_0 = 0
	n_category_1 = 0
	y = []
	for item in click_number_list:
		if item <= median:
			n_category_0 = n_category_0 + 1
			y.append(0)
		else:
			n_category_1 = n_category_1 + 1
			y.append(1)
	p_category_0 = n_category_0 * 1.0 / (n_category_0 + n_category_1)
	
	# clf = DecisionTreeRegressor(max_depth = 3)
	# clf = tree.DecisionTreeClassifier(max_depth=13, criterion='entropy', min_samples_leaf=1, min_samples_split=15)
	clf = tree.DecisionTreeClassifier(max_depth=None, criterion='entropy', min_samples_leaf=20, min_samples_split=15)
	# clf = svm.SVC(kernel='rbf', C=1)
	
	# validate code

	scores = cross_validation.cross_val_score(clf, X, y, cv=10)
	print 'category_0: %f, n_category_1: %f' % (p_category_0, 1 - p_category_0)
	print 'Avg accuracy: %f' % scores.mean()
	print 'median: %d' % median
	clf.fit(X, y)
	predicted = clf.predict(X)
	print 'On training set: %f' % (numpy.mean(predicted == y))

	# # dump tree modle
	# output = open('%s/%s.pkl' % (result_path, category_name), 'w')
	# pickle.dump(clf, output)
	# output.close()

	# visualize
	with open('%s/%s.dot' % (result_path, category_name), 'w') as f:
		f = tree.export_graphviz(clf, out_file = f, feature_names=feature_names)
	os.system('dot -Tpdf %s/%s.dot -o %s/%s.pdf' % (result_path, category_name, result_path, category_name))

def bin_data(univariate_x, y, bins):
	# 根据x排序，对y也排序
	combine = zip(univariate_x, y)
	combine.sort(key = lambda t: t[0])
	# bin之后的x对应一个y的列表
	# use data with outliers omitted
	combine = combine[int(len(combine) * 0.05) : int(len(combine) * 0.95)]

	step = (combine[-1][0] - combine[0][0]) * 1.0 / bins
	basket = []
	# print combine[-1][0]
	# print combine[0][0]
	# print step
	# print '------------'
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

def another_bin_data(univariate_x, y, bins):
	# 根据X参数数据量平分十份
	# 根据x排序，对y也排序
	combine = zip(univariate_x, y)
	combine.sort(key = lambda t: t[0])
	# bin之后的x对应一个y的列表
	# use data with outliers omitted
	combine = combine[int(len(combine) * 0.05) : int(len(combine) * 0.95)]

	number_each_bin = len(combine) / bins
	rt_X = []
	rt_Y = []
	k = 0
	while (k + number_each_bin < len(combine)):
		rt_Y.append([])
		tmp = 0
		for item in combine[k : k + number_each_bin]:
			rt_Y[-1].append(item[1])
			tmp = tmp + item[0]
		tmp = tmp * 1.0 / number_each_bin
		rt_X.append(tmp)
		k = k + number_each_bin
	rt_Y.append([])
	tmp = 0
	for item in combine[k : ]:
		rt_Y[-1].append(item[1])
		tmp = tmp + item[0]
	tmp = tmp * 1.0 / (len(combine) - k)
	rt_X.append(tmp)
	return rt_X, rt_Y

def plot_confidence_interval(wifi_data_list, click_number_list, category_name):
	print 'plot confidence interval: %s' % category_name
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])

	os.system('mkdir ../figure/confidence_interval/%s' % category_name)
	f_info = open('../figure/confidence_interval/%s/%s.txt' % (category_name, category_name), 'w')
	for i in range(para_number):
		rt_X, rt_Y = bin_data(para_record[i], click_number_list, 10)
		# print 'parameter: %s' % feature_names[i]
		f_info.write('parameter: %s\n' % feature_names[i])
		lower_list = []
		mid_list = []
		upper_list = []
		info = ''
		for j in range(len(rt_X)):
			info = info + ('%f: %d, ' % (rt_X[j], len(rt_Y[j])))
			mid, lower, upper = mean_confidence_interval(rt_Y[j])
			lower_list.append(lower)
			mid_list.append(mid)
			upper_list.append(upper)
			# tmp_X = [rt_X[j], rt_X[j], rt_X[j]]
			# tmp_Y = [mid, lower, upper]
			# plt.scatter(tmp_X, tmp_Y)
		# for j in range(len(rt_X)):
			# for item in rt_Y[j]:
				# plt.scatter(rt_X[j], item)
		# print info
		f_info.write('%s\n' % info)
		plt.plot(rt_X, lower_list)
		plt.plot(rt_X, mid_list)
		plt.plot(rt_X, upper_list)
		plt.savefig('../figure/confidence_interval/%s/%s.pdf' % (category_name, feature_names[i]))
		plt.clf()
	f_info.close()

def plot_p25_p75(wifi_data_list, click_number_list, category_name):
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])

	os.system('mkdir ../figure/p25_p75/%s' % category_name)
	for i in range(para_number):
		rt_X, rt_Y = bin_data(para_record[i], click_number_list, 10)
		mid_list = []
		lower_list = []
		upper_list = []
		for j in range(len(rt_X)):
			rt_Y[j].sort()
			print rt_Y[j]
			len_rt_Y_j = len(rt_Y[j])
			mid = rt_Y[j][int(len_rt_Y_j * 0.5)]
			lower = rt_Y[j][int(len_rt_Y_j * 0.25)]
			upper = rt_Y[j][int(len_rt_Y_j * 0.75)]
			mid_list.append(mid)
			lower_list.append(lower)
			upper_list.append(upper)
			# mid, lower, upper = mean_confidence_interval(rt_Y[j])
			# tmp_X = [rt_X[j], rt_X[j], rt_X[j]]
			# tmp_Y = [lower, mid, upper]
			# plt.scatter(tmp_X, tmp_Y)
		# for j in range(len(rt_X)):
			# for item in rt_Y[j]:
				# plt.scatter(rt_X[j], item)
		plt.plot(rt_X, lower_list)
		plt.plot(rt_X, mid_list)
		plt.plot(rt_X, upper_list)
		plt.axis([0, 0.1, 0, 10])
		plt.savefig('../figure/p25_p75/%s/%s.pdf' % (category_name, feature_names[i]))
		plt.clf()

# f_corrceof = open('%s/corrcoef.txt' % result_path, 'w')
def compute_pearson_correlation(wifi_data_list, click_number_list, category_name):
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
		coef, p_value = stats.pearsonr(para_record[i], click_number_list)
		corrcoef_list.append(coef)
		result = result + '\t' + (str)(coef)
		# print feature_names[i]
	return corrcoef_list
	# f_corrceof.write('%s\n' % category_name)
	# f_corrceof.write('%s\n' % result)

def compute_kendall_correlation(wifi_data_list, click_number_list, category_name):
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
		rt_X, rt_Y = bin_data(para_record[i], click_number_list, 10)
		final_X = []
		final_Y = []

		# for j in range(len(rt_X)):
			# for item in rt_Y[j]:
				# final_X.append(rt_X[j])
				# final_Y.append(item)

		# calculate average for each bin
		final_X = rt_X
		for item in rt_Y:
			final_Y.append(numpy.mean(item))
		coef, p_value = stats.kendalltau(final_X, final_Y)
		corrcoef_list.append(coef)
		result = result + '\t' + (str)(coef)
		# print feature_names[i]
	print max([abs(t) for t in corrcoef_list])
	return corrcoef_list

def compute_relative_information_gain(wifi_data_list, click_number_list, category_name):
	print 'relative information gain'
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
		rt_X, rt_Y = bin_data(para_record[i], click_number_list, 10)
		final_X = []
		final_Y = []
		for j in range(len(rt_X)):
			for item in rt_Y[j]:
				final_X.append(rt_X[j])
				final_Y.append(item)
		# final_X = para_record[i]
		# final_Y = click_number_list
		H_Y = metrics.mutual_info_score(final_Y, final_Y)
		info_gain = metrics.mutual_info_score(final_Y, final_X)
		coef = info_gain / H_Y

		corrcoef_list.append(coef)
		result = result + '\t' + (str)(coef)
		# print feature_names[i]
	print max([abs(t) for t in corrcoef_list])
	return corrcoef_list

def scatter_plot(wifi_data_list, click_number_list, category_name):
	para_number = len(wifi_data_list[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in wifi_data_list:
		for i in range(para_number):
			para_record[i].append(item[i])
	os.system('mkdir ../figure/scatter_05_95/%s' % category_name)
	for i in range(para_number):
		
		tmp = zip(para_record[i], click_number_list)
		tmp.sort(key = lambda t: t[0])
		s_index = int(len(tmp) * 0.05)
		t_index = int(len(tmp) * 0.95)
		tmp = tmp[s_index : t_index]
		X_data = [data[0] for data in tmp]
		Y_data = [data[1] for data in tmp]
		coordinates_to_file(X_data, Y_data, '../figure/scatter_05_95/%s/%s.csv' % (category_name, feature_names[i]))
		plt.scatter(X_data, Y_data)

		# plt.scatter(para_record[i], click_number_list)
		plt.savefig('../figure/scatter_05_95/%s/%s_%s.pdf' % (category_name, category_name, feature_names[i]))
		plt.clf()

def aggregate_records():
	portal_lines = []
	portal_lines = portal_lines + read_records_of_a_site('sina')
	portal_lines = portal_lines + read_records_of_a_site('163')
	# portal_lines = portal_lines + read_records_of_a_site('qq')
	process_data(portal_lines, 'portal')

	video_lines = []
	video_lines = video_lines + read_records_of_a_site('bilibili')
	video_lines = video_lines + read_records_of_a_site('acfun')
	video_lines = video_lines + read_records_of_a_site('tudou')
	video_lines = video_lines + read_records_of_a_site('youku')
	process_data(video_lines, 'video')

	shop_lines = []
	# shop_lines = shop_lines + read_records_of_a_site('amazon')
	shop_lines = shop_lines + read_records_of_a_site('taobao')
	shop_lines = shop_lines + read_records_of_a_site('tmall')
	shop_lines = shop_lines + read_records_of_a_site('jd')
	process_data(shop_lines, 'shop')

	social_lines = []
	social_lines = social_lines + read_records_of_a_site('weibo')
	social_lines = social_lines + read_records_of_a_site('zhihu')
	process_data(social_lines, 'social')


def traverse_analyze():
	for site in top_sites:
		site_lines = read_records_of_a_site(site)
		process_data(site_lines, site)

def accumulate():
	# Kendall
	para_number = len(kendall_record[0][0])
	tmp_list = []
	for i in range(para_number):
		origin_X = []
		for record in kendall_record:
			for k in range(record[1]):
			# for k in range(1):
				origin_X.append(record[0][i])
		X, Y = compute_cdf(origin_X)
		tmp, = plt.plot(X, Y, label='%s' % feature_names[i])
		tmp_list.append(tmp)
		plt.legend([tmp], [feature_names[i]], 'lower right')
		plt.savefig('../figure/kendall_cdf/session_%s.pdf' % feature_names[i])
		plt.clf()
	# plt.savefig('../figure/kendall_cdf/session_aggregate.pdf')
	# plt.legend(tmp_list, feature_names, 'lower right')
	# plt.savefig('../figure/kendall_cdf/session_aggregate_legend.pdf')	
	# plt.clf()

	# Relative Information Gain
	para_number = len(info_gain_record[0][0])
	tmp_list = []
	for i in range(para_number):
		origin_X = []
		for record in info_gain_record:
			for k in range(record[1]):
			# for k in range(1):
				origin_X.append(record[0][i])
		X, Y = compute_cdf(origin_X)
		tmp, = plt.plot(X, Y, label='%s' % feature_names[i])
		tmp_list.append(tmp)
		plt.legend([tmp], [feature_names[i]], 'lower right')
		plt.savefig('../figure/info_gain_cdf/session_%s.pdf' % feature_names[i])
		plt.clf()
	# plt.savefig('../figure/info_gain_cdf/session_aggregate.pdf')
	# plt.legend(tmp_list, feature_names, 'lower right')
	# plt.savefig('../figure/info_gain_cdf/session_aggregate_legend.pdf')
	# plt.clf()

def initialize():
	for i in range(len(feature_names)):
		feature_dict[feature_names[i]] = i

if __name__ == '__main__':
	# lines = find_delay_records('1433521311', '1433521408', '08BD43CCEAD0')
	# print lines

	initialize()

	site_lines = []
	for site in top_sites:
		site_lines = site_lines + read_records_of_a_site(site)
	process_data(site_lines, 'all')
	# aggregate_records()

	# traverse_analyze()
	# accumulate()

	# f_corrceof.close()