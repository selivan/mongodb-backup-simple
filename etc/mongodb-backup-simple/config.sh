services=''
for i in /etc/init/mongodb.rs*; do
    s=$(basename $i)
    s=${s%.conf}
    services="$services $s"
done

# no trailing slashes here:
data=/opt/mongodb.rs*

mongodump_opts="--ipv6 --host mongo-configsvr.example.com --port 27019 --username root --password root --authenticationDatabase admin"

backup_dir=/opt/backup/mongo/

status=/var/log/mongodb-backup-simple/LAST_BACKUP_STATUS
rsync_status=/var/log/mongodb-backup-simple/RSYNC_DONE

rotate=0
rotate_depth=7

backup_expire=$((3600*36))
