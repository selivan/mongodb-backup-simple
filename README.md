Simple mongodb backup
---------------------

Works on single server, running secondaries for all shards. Backup is done by simple copying with rsync. `db.fsyncLock()` is used to freeze servers before backup, so they continue recieving oplog and voting. Config server is backed up by mongodump.

Fails if Balancer is runniing - because it can lead to inconsistent backup.

Tested with mongo 2.6 and pymongo 2.6. Probably will work with 3.0.

Notice: this version doesn't do backup rotation.

Config
------
* backup directory
* file to create on backup success
* mongod servers:
  * data catalogs to backup
  * connection credentials: ip, port, db, user, password
* config servers
  * connection credentials: ip, port, db, user, password
* rsync options to backup 
* mongodump options to backup config servers

Links
-----
* https://api.mongodb.org/python/2.6.3/
* https://groups.google.com/forum/#!msg/mongodb-user/ukG2D459J_w/62NiSO3dyBkJ
* http://pyyaml.org/wiki/PyYAMLDocumentation

**P.S.** If this code is useful for you - don't forget to put a star on it's [github repo](https://github.com/selivan/mongodb-backup-simple).
