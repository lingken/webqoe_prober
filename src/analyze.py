import pickle
import re
import os
import sys
from bisect import bisect
from sklearn import tree
from sklearn.tree import DecisionTreeRegressor
from sklearn.externals.six import StringIO

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
	# for item in lines[start_index-2 : start_index + 2] + lines[end_index-2 : end_index + 2]:
		# print item
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
		return None

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
		return None
	AP_file_list = os.listdir(AP_file_path)
	# print AP_file_list
	if ('station.txt' not in AP_file_list) or ('channel.txt' not in AP_file_list):
		print 'No station.txt or channel.txt'
		print line
		return None

	channel_records = find_records('channel.txt', start_time, end_time, MAC, AP_MAC)
	if (len(channel_records) == 0):
		print 'len(channel_records) == 0'
		print line
		return None
	# channel: timestamp, active, busy, rx_time, tx_time
	channel_start = channel_records[0].split(',')
	channel_end = channel_records[-1].split(',')
	channel_duration = (int)(channel_end[0]) - (int)(channel_start[0])
	if channel_duration == 0:
		print 'channel_duration == 0'
		print line
		return None
	# channel_active = ((int)(channel_end[1]) - (int)(channel_start[1])) * 1.0 / channel_duration
	# channel_busy = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / channel_duration
	channel_rxtime = ((int)(channel_end[3]) - (int)(channel_start[3])) * 1.0 / channel_duration
	channel_txtime = ((int)(channel_end[4]) - (int)(channel_start[4])) * 1.0 / channel_duration
	channel_air_utilization = ((int)(channel_end[2]) - (int)(channel_start[2])) * 1.0 / ((int)(channel_end[1]) - (int)(channel_start[1]))

	station_records = find_records('station.txt', start_time, end_time, MAC, AP_MAC)
	# station: 0-timestamp, 1-devMAC, 2-receive_byte, 3-send_byte, 4-send_packet, 5-resend_packet, 6-signal, 7-send_phyrate, 8-receive_phyrate
	station_startindex = -1
	station_endindex = -1

	DEV_MAC = MAC.replace(':', '').lower()
	# print DEV_MAC
	for i in range(len(station_records)):
		if station_records[i].find(DEV_MAC) >= 0:
			station_startindex = i
	for i in range(len(station_records) - 1, -1, -1):
		if station_records[i].find(DEV_MAC) >= 0:
			station_endindex = i
	
	if station_startindex < 0:
		print 'No Dev'
		return None

	# if station_startindex == station_endindex:
	# 	print 'station_startindex == station_endindex'
	# 	print line
	# 	return None

	station_start = station_records[station_startindex].split(',')
	station_end = station_records[station_endindex].split(',')
	# station_duration = (int)(station_end[0]) - (int)(station_start[0])
	# station_rxbyte = ((int)(station_end[2]) - (int)(station_start[2])) * 1.0 / station_duration
	# station_txbyte = ((int)(station_end[3]) - (int)(station_start[3])) * 1.0 / station_duration
	# station_send_packet = ((int)(station_end[4]) - (int)(station_start[4])) * 1.0 / station_duration
	# station_resend_packet = ((int)(station_end[5]) - (int)(station_start[5])) * 1.0 / station_duration

	station_record_number = 0
	station_signal_strength = 0
	station_send_phyrate = 0
	station_receive_phyrate = 0

	for item in station_records:
		if item.find(DEV_MAC) < 0:
			continue
		tmp_station_record = item.split(',')
		station_record_number = station_record_number + 1
		station_signal_strength = station_signal_strength + (int)(tmp_station_record[6])
		station_send_phyrate = station_send_phyrate + (float)(tmp_station_record[7])
		station_receive_phyrate = station_receive_phyrate + (float)(tmp_station_record[8])

	station_signal_strength = station_signal_strength * 1.0 / station_record_number
	station_send_phyrate = station_send_phyrate * 1.0 / station_record_number
	station_receive_phyrate = station_receive_phyrate * 1.0 / station_record_number

	# print 'channel - active: %f, busy: %f, rx_time: %f, tx_time: %f' % (channel_active, channel_busy, channel_rxtime, channel_txtime)
	# print 'station - recByte: %f, sndByte: %f, sndPkt: %f, rsndPkt: %f, signal: %f, sndPhy: %f, recPhy: %f' % (station_rxbyte, station_txbyte, station_send_packet, station_resend_packet, station_signal_strength, station_send_phyrate, station_receive_phyrate)
	rt = []
	# rt.append(channel_active) # 0
	# rt.append(channel_busy) # 1
	rt.append(channel_air_utilization)
	rt.append(channel_rxtime)
	rt.append(channel_txtime)
	# rt.append(station_rxbyte)
	# rt.append(station_txbyte)
	# rt.append(station_send_packet)
	# rt.append(station_resend_packet)
	rt.append(station_signal_strength)
	rt.append(station_send_phyrate)
	rt.append(station_receive_phyrate)
	return rt

regex_click_number = re.compile(r'click_number: (\d*),')	

Line_number = 0
None_number = 0
def regress_data(lines, category_name):
	global Line_number
	global None_number
	X = []
	y = []
	for line in lines:
		match = re.match(regex_click_number, line)
		click_number = (int)(match.group(1))
		wifipara = get_wireless_record(line)
		Line_number = Line_number + 1
		if wifipara is not None:
			# try to use regressor or classifier
			y.append(click_number)
			X.append(wifipara)
		else:
			# print 'None'
			None_number = None_number + 1

	clf = DecisionTreeRegressor(max_depth = 3)
	clf.fit(X, y)

	# dump tree modle
	output = open('%s.pkl' % category_name, 'w')
	pickle.dump(clf, output)
	output.close()

	# visualize
	with open('%s.dot' % category_name, 'w') as f:
		f = tree.export_graphviz(clf, out_file = f)


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
	regress_data(portal_lines, 'portal')

	video_lines = []
	video_lines = video_lines + read_records_of_a_site('bilibili')
	video_lines = video_lines + read_records_of_a_site('acfun')
	video_lines = video_lines + read_records_of_a_site('tudou')
	video_lines = video_lines + read_records_of_a_site('youku')
	regress_data(video_lines, 'video')

	shop_lines = []
	shop_lines = shop_lines + read_records_of_a_site('amazon')
	shop_lines = shop_lines + read_records_of_a_site('taobao')
	shop_lines = shop_lines + read_records_of_a_site('tmall')
	shop_lines = shop_lines + read_records_of_a_site('jd')
	regress_data(shop_lines, 'shop')

if __name__ == '__main__':
	# print 'analyze'
	# get_wifidata_path_tree_ready()
	# s = 'click_number: 1, time: 1433047054 - 1433047062, Info: qq len: 13 MAC: 68:df:dd:6a:5e:ef AP_MAC: 6CB0CE0FB50A'
	# print get_wireless_record(s)
	aggregate_records()
	print 'Line: %d, None: %d' % (Line_number, None_number)
