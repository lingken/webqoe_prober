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

path = '../compress_wifidata'
wifidata_path = {}
starttime_list = []
def get_wifidata_path_tree_ready():
	starttime_list.extend(os.listdir(path))
	starttime_list.sort()
	for item in starttime_list:
		time_path = path + '/' + item
		if not os.path.isdir(time_path):
			continue
		router_list = os.listdir(time_path)
		wifidata_path[item] = set(router_list)

	# for item in starttime_list:
	# 	print item
	# 	if item in wifidata_path:
	# 		for router in wifidata_path[item]:
	# 			print '\t' + router

def find_records(file_name, start_time, end_time, device_MAC, AP_MAC):
	file_path = '../wifidata/%s/%s' % (AP_MAC, file_name)
	f = open(file_path, 'r')
	lines = f.readlines()
	f.close()

	# start_time and end_time are string
	start_index = bisect(lines, start_time)
	end_index = bisect(lines, end_time)
	return lines[start_index - 1 : end_index + 1] # The index may overflow

regex_click_record = re.compile(r'click_number: (\d*), time: (\d*) - (\d*), Info: (\w*) len: (\d*) MAC: (.*) AP_MAC: (.*)$')
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
	# print 'click_number: %s, time: %s - %s, site: %s, visit_length: %s, MAC: %s AP_MAC: %s\n' % (click_number, start_time, end_time, site, visit_length, MAC, AP_MAC)
	
	# print starttime_list
	# index = bisect(starttime_list, start_time)
	# if index < 0:
	# 	return None
	# file_starttime = starttime_list[index - 1]
	# print starttime_list
	# print file_starttime
	# MAC_foldername = AP_MAC
	# if MAC_foldername in wifidata_path[file_starttime]:
	# 	file_path = path + '/' + file_starttime + '/' + MAC_foldername
	# 	return file_path
	# return None

	# for file_starttime in starttime_list:
	# 	if file_starttime not in wifidata_path:
	# 		continue
	# 	if AP_MAC not in wifidata_path[file_starttime]:
	# 		continue
	# 	tmp_file_path = path + '/' + file_starttime + '/' + AP_MAC + '/wlan0/q'
	# 	f = open(tmp_file_path, 'r')
	# 	lines = f.readlines()
	# 	f.close()
	# 	tmp_start_time = (int)(lines[0].split(',')[0])
	# 	tmp_end_time = (int)(lines[-1].split(',')[0])
	# 	print tmp_file_path
	# 	print '\t' + lines[0], tmp_start_time
	# 	print '\t' + lines[-1], tmp_end_time

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
	station_signal_strength = station_signal_strength[len(station_signal_strength) / 2] # list to mid_value

	station_send_phyrate = station_send_phyrate * 1.0 / station_record_number
	station_receive_phyrate = station_receive_phyrate * 1.0 / station_record_number

	# print 'channel - active: %f, busy: %f, rx_time: %f, tx_time: %f' % (channel_active, channel_busy, channel_rxtime, channel_txtime)
	# print 'station - recByte: %f, sndByte: %f, sndPkt: %f, rsndPkt: %f, signal: %f, sndPhy: %f, recPhy: %f' % (station_rxbyte, station_txbyte, station_send_packet, station_resend_packet, station_signal_strength, station_send_phyrate, station_receive_phyrate)
	rt = []
	feature_names = []
	
	# rt.append(channel_active)
	# feature_names.append('channel_active')
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

regex_click_number = re.compile(r'click_number: (\d*),')	

Line_number = 0
None_number = 0
Omit_number = 0
def regress_data(lines, category_name):
	global Line_number
	global None_number
	global Omit_number
	X = []
	y = []
	feature_names = []
	for line in lines:
		match = re.match(regex_click_number, line)
		click_number = (int)(match.group(1))
		Line_number = Line_number + 1

		# get rid of dirty data
		if click_number > 20:
			Omit_number = Omit_number + 1
			continue

		wifipara, tmp = get_wireless_record(line)
		if (tmp != None):
			feature_names = tmp
		if wifipara is not None:
			# try to use regressor or classifier
			# if click_number <= 3:
			# 	y.append(0)
			# elif click_number <= 7:
			# 	y.append(1)
			# else:
			# 	y.append(2)

			if click_number <= 1:
				y.append(0)
			else:
				y.append(1)
			# y.append(click_number)

			X.append(wifipara)
		else:
			# print 'None'
			None_number = None_number + 1

	# clf = DecisionTreeRegressor(max_depth = 3)
	clf = tree.DecisionTreeClassifier(max_depth=None, criterion='entropy', min_samples_leaf=1)
	
	# validate code
	# combine = zip(X, y)
	# correct_list = []
	# pivot = int(0.9 * len(combine))
	# for i in range(10):
	# 	answer = []
	# 	shuffle(combine)
	# 	clf.fit([data[0] for data in combine[:pivot]], [data[1] for data in combine[:pivot]])
	# 	predicted = clf.predict([data[0] for data in combine[pivot:]])
	# 	for item in [data[1] for data in combine[pivot:]]:
	# 		if item <= 1:
	# 			answer.append(0)
	# 		else:
	# 			answer.append(1)
	# 	rate = numpy.mean(predicted == answer)
	# 	print rate
	# 	correct_list.append(rate)

	# print 'final avg: %f' % numpy.mean(correct_list)



	clf.fit(X, y)

	# # dump tree modle
	# output = open('%s/%s.pkl' % (result_path, category_name), 'w')
	# pickle.dump(clf, output)
	# output.close()

	# visualize
	with open('%s/%s.dot' % (result_path, category_name), 'w') as f:
		f = tree.export_graphviz(clf, out_file = f, feature_names=feature_names)
	os.system('dot -Tpdf %s/%s.dot -o %s/%s.pdf' % (result_path, category_name, result_path, category_name))

f_corrceof = open('%s/corrcoef.txt' % result_path, 'w')
def compute_correlation(lines, category_name):
	print category_name
	X = []
	y = []
	feature_names = []
	for line in lines:
		match = re.match(regex_click_number, line)
		click_number = (int)(match.group(1))

		# get rid of dirty data
		if click_number > 20:
			continue

		wifipara, tmp = get_wireless_record(line)
		if (tmp != None):
			feature_names = tmp
		if wifipara is not None:
			# try to use regressor or classifier
			y.append(click_number)
			X.append(wifipara)
	# print X
	# print y
	if len(X) == 0:
		return

	para_number = len(X[0])
	para_record = []
	for i in range(para_number):
		para_record.append([])
	for item in X:
		for i in range(para_number):
			para_record[i].append(item[i])
	
	corrcoef_list = []
	result = ''
	os.system('mkdir ../figure/%s' % category_name)
	for i in range(para_number):
		coef = stats.pearsonr(para_record[i], y)
		corrcoef_list.append(coef)
		result = result + '\t' + (str)(coef[0])
		print feature_names[i]
		plt.scatter(para_record[i], y)
		# plt.show()
		plt.savefig('../figure/%s/%s_%s.pdf' % (category_name, category_name, feature_names[i]))
		plt.clf()
	f_corrceof.write('%s\n' % category_name)
	f_corrceof.write('%s\n' % result)

def read_records_of_a_site(site_name):
	f = open('../click_record/%s.txt' % site_name, 'r')
	lines = f.readlines()
	f.close()
	return lines

def aggregate_records():
	portal_lines = []
	portal_lines = portal_lines + read_records_of_a_site('sina')
	portal_lines = portal_lines + read_records_of_a_site('163')
	portal_lines = portal_lines + read_records_of_a_site('qq')
	# regress_data(portal_lines, 'portal')
	compute_correlation(portal_lines, 'portal')

	video_lines = []
	video_lines = video_lines + read_records_of_a_site('bilibili')
	video_lines = video_lines + read_records_of_a_site('acfun')
	video_lines = video_lines + read_records_of_a_site('tudou')
	video_lines = video_lines + read_records_of_a_site('youku')
	# regress_data(video_lines, 'video')
	compute_correlation(video_lines, 'video')

	shop_lines = []
	shop_lines = shop_lines + read_records_of_a_site('amazon')
	shop_lines = shop_lines + read_records_of_a_site('taobao')
	shop_lines = shop_lines + read_records_of_a_site('tmall')
	shop_lines = shop_lines + read_records_of_a_site('jd')
	# regress_data(shop_lines, 'shop')
	compute_correlation(shop_lines, 'shop')

	social_lines = []
	social_lines = social_lines + read_records_of_a_site('weibo')
	social_lines = social_lines + read_records_of_a_site('zhihu')
	compute_correlation(social_lines, 'social')

def statistical_analyze():
	for site in top_sites:
		site_lines = read_records_of_a_site(site)
		compute_correlation(site_lines, site)
		# regress_data(site_lines, 'simple_' + site)
		# regress_data(site_lines, 'diverse_' + site)
		# regress_data(site_lines, 'regress_' + site)

def statistic(category_name):
	file_path = '../click_record/%s.txt' % (category_name)
	f = open(file_path, 'r')
	lines = f.readlines()
	f.close()
	click_number_list = []
	for line in lines:
		match = re.match(regex_click_number, line)
		if match is None:
			continue
		click_number_list.append((int)(match.group(1)))
	click_number_list.sort()
	print click_number_list
	print click_number_list[int(len(click_number_list) * 0.75)]
	print numpy.mean(click_number_list)

if __name__ == '__main__':
	# get_wifidata_path_tree_ready()
	# s = 'click_number: 1, time: 1433047054 - 1433047062, Info: qq len: 13 MAC: 68:df:dd:6a:5e:ef AP_MAC: 6CB0CE0FB50A'
	# aggregate_records()
	# statistical_analyze()
	# print 'Line: %d, None: %d, Omit: %d\n' % (Line_number, None_number, Omit_number)

	# site_lines = read_records_of_a_site('acfun')
	# compute_correlation(site_lines, 'acfun')

	# regress_data(site_lines, 'weibo')

	# statistic('weibo')
	# site_lines = []
	# for site in top_sites:
		# site_lines = site_lines + read_records_of_a_site(site)
	# compute_correlation(site_lines, 'all')

	f_corrceof.close()