services=''
for i in /etc/init/mongodb.rs*; do
    s=$(basename $i)
    s=${s%.conf}
    services="$services $s"
done

# no trailing slashes here:
data=/opt/mongodb-moddb.rs*

mongodump_opts="--ipv6 --port 27019 --username root -proot --authenticationDatabase admin"
configsvr_hosts="mongocfg0.example.com mongocfg1.example.com mongocfg2.example.com"

backup_dir=/local/backup/rsnap/mongo/moddb/tmp

status=/var/log/mongo-backup/LAST_BACKUP_STATUS
backup_ok="$backup_dir/.rsnap_prot0"
rsync_status=/var/log/mongo-backup/RSYNC_DONE

rotate=0
rotate_depth=7

backup_expire=$((3600*36))
