#!/bin/bash
# Config file name may be passed as first parameter

[ -n "$1" ] && source "$1" || source /etc/mongodb-backup-simple/config.sh

if [ ! -f "$status" ]; then
	echo "2; Status file $status not found"
	exit
fi

filemtime=`stat -c %Y $status`
currtime=`date +%s`
diff=$(($currtime - $filemtime))

if [ $diff -gt $backup_expire ]; then
	echo "2; Status file $status is older than $backup_expire seconds"
fi

cat $status
