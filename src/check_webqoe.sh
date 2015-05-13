PRO_PATH="/root/webqoe"
PROGRAM="daemon_webqoe"

PRO_NOW=`ps | grep $PROGRAM | grep -v grep | wc -l`
if [ $PRO_NOW -lt 1 ]; then
	echo "restart daemon_webqoe"
	$PRO_PATH/daemon_webqoe.sh
else
	echo "daemon_webqoe is running"
fi

exit