#!/bin/bash
# Config file name may be passed as first parameter

[ -n "$1" ] && source "$1" || source /etc/mongodb-backup-simple/config.sh

function die() {
    echo $*
    echo "2; $*" > $status
    exit 1
}

set -x

which rsync >/dev/null || die 'rsync not found'
which mongodump >/dev/null || die 'mongodump not found'

for s in $services; do
    service $s stop || die "failed to stop $s"
done

if [ "$rotate" == '1' ]; then
    dest="$backup_dir/tmp"
else
    dest="$backup_dir"
fi

# Run rsync in background
[ -f $rsync_status ] && rm $rsync_status
(rsync -a $data "$dest" ; echo $? > $rsync_status) &
rsync_pid=$!

mongodump --oplog $mongodump_opts --out "$backup_dir/tmp/configsvr"
if [ $? -ne 0 ]; then
    kill -SIGTERM $rsync_pid
    for s in $services; do
        service $s start
    done
    die "mongodump failed"
fi

echo "Waiting for rsync to finish..."
while [ -d /proc/$rsync_pid ]; do
	sleep 5
done
sleep 1

if [ "$(cat $rsync_status)" != '0' ]; then
    for s in $services; do
        service $s start
    done
    die "rsync failed"
fi

for s in $services; do
    service $s start
done

# Rotate backups
if [ "$rotate" == '1' ]; then
    seq $rotate_depth -1 0 | wc -l > /dev/null || die "Can not rotate backups: $rotate_depth is not a valid number"

    for i in $(seq $rotate_depth -1 0); do
        [ -d "$backup_dir/$i" ] && mv "$backup_dir/$i" "$backup_dir/$((i+1))"
    done
    mv "$backup_dir/tmp" "$backup_dir/0"
    rm --preserve-root -fr "$backup_dir/$((rotate_depth+1))"
fi

echo "0; OK" > $status
