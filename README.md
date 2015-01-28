Simple mongodb backup
---------------------

Works on single server, running secondaries for all shards. Config server is backed up by mongodump.
Script rotates backups for according to settings in config file. Check script returning last backup state included.

Config
------
* services to stop (mongod instances)
* catalogs to backup
* mongodump options to backup config database
* status file for monitoring
* status file for rsync
* backups catalog
* enable/disable backup rotation
* how many copies to keep while rotating
* backup expiration time for monitoring

Monitoring
----------
* Last backup status
* Last backup age (expiration time set in config)

TODO
----
* Try to connect to several config servers, until success.
