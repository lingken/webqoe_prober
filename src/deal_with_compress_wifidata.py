import re
import os
import sys

router_set = set()

def process_data():
	path = '../compress_wifidata'
	
	filetime_list = os.listdir(path)
	# print filetime_list
	for item in filetime_list:
		timepath = path + '/' + item
		if not os.path.isdir(timepath):
			continue
		# print item
		router_list = os.listdir(timepath)
		for router in router_list:
			router_path = timepath + '/' + router
			if os.path.isdir(router_path):
				router_set.add(router)

	for router in router_set:
		print router
		# # Debug
		# if router != '6CB0CE114D59':
		# 	continue

		router_record_list = [[], [], [], [], []] # channel, q, rx, station, tx
		file_name_list = ['channel', 'q', 'rx', 'station', 'tx']
		
		for item in filetime_list:
			for i in range(len(file_name_list)):
				file_path = path + '/' + item + '/' + router + '/wlan0/' + file_name_list[i]
				try:
					f = open(file_path, 'r')
					router_record_list[i] = router_record_list[i] + f.readlines()
					f.close()
				except IOError, e:
					pass

		os.system('mkdir ../wifidata/%s' % router)
		for i in range(len(router_record_list)):
			router_record_list[i] = list(set(router_record_list[i]))
			router_record_list[i].sort()

			if (len(router_record_list[i]) > 0):
				new_file_path = '../wifidata/%s/%s.txt' % (router, file_name_list[i])
				f = open(new_file_path, 'w')
				for line in router_record_list[i]:
					f.write(line)
				f.close()



if __name__ == '__main__':
	process_data()
	print router_set