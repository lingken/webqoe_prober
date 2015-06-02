import pickle
import re
from sklearn import tree
from sklearn.tree import DecisionTreeRegressor
from sklearn.externals.six import StringIO
def regress(X, y):
	clf = DecisionTreeRegressor(max_depth = 5)
	clf.fit(X, y)

	# dump tree modle
	output = open('tree.pkl', 'w')
	pickle.dump(clf, output)
	output.close()

	# visualize
	with open('tree_graph.dot', 'w') as f:
		f = tree.export_graphviz(clf, out_file = f)

regex_click_record = re.compile(r'click_number: (\d*), time: (\d*) - (\d*), Info: (\w*) len: (\d*) MAC: (.*)$')
def get_wireless_record(line):
	match = re.match(regex_click_record, line)
	click_number = 0;
	start_time = 0;
	end_time = 0;
	site = 'N/A';
	visit_length = 0;
	MAC = 'NULL';
	if match is not None:
		click_number = match.group(1);
		start_time = match.group(2);
		end_time = match.group(3);
		site = match.group(4);
		visit_length = match.group(5);
		MAC = match.group(6)

	print 'click_number: %s, time: %s - %s, site: %s, visit_length: %s, MAC: %s\n' % (click_number, start_time, end_time, site, visit_length, MAC)
if __name__ == '__main__':
	# print 'analyze'
	s = 'click_number: 1, time: 1433047054 - 1433047062, Info: qq len: 13 MAC: 68:df:dd:6a:5e:ef'
	get_wireless_record(s)