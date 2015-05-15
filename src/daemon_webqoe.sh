PRO_PATH="/root/webqoe"
PROGRAM="webqoe_prober"
MAC=`ifconfig wlan0 | grep HWaddr | awk '{print $5}'|sed 's/://g'`
INTERFACE="wlan0"
PACKET_NUMBER="10000"

while true; do
	PRO_NOW=`ps | grep $PROGRAM | grep -v grep | wc -l`
	if [ $PRO_NOW -lt 1 ]; then
		echo "restart program"
		mkdir $PRO_PATH/$MAC
		echo "123" > $PRO_PATH/rsync_pass
		chmod 600 $PRO_PATH/rsync_pass

		/usr/bin/rsync -zzr --progress $PRO_PATH/$MAC lk@166.111.9.242::lk --password-file=$PRO_PATH/rsync_pass
		rm $PRO_PATH/$MAC/*
		# ./$PROGRAM 2>/dev/null 1>&2 &
		# TIME=`date +%Y%m%d-%H-%M-%S`
		/usr/sbin/$PROGRAM $MAC $INTERFACE $PACKET_NUMBER 2>/dev/null 1>&2 &
	else
		echo "webqoe_prober is running"
	fi
	sleep 5
done

exit