#!/usr/bin/env python2
from optparse import OptionParser
import yaml

import logging
import socket
import sys
from pprint import pformat

from subprocess import Popen, PIPE
import pymongo

def die(msg, exit_code=1):
    logging.error(msg)
    sys.exit(exit_code)


def host2ip(hostname):
    '''Convert hostname to ip address, prefer iPv6.
    IPv6 address is enclosed in []
    Return None if failed.'''
    try:
        return '[' + socket.getaddrinfo(hostname, None, socket.AF_INET6)[0][4][0] + ']'
    except:
        try:
            return socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
        except:
            return None


# default settings
CONFIG_FILE = '/etc/mongo-backup-simple/config.yml'

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

    logging.info('Backup started')

    # parse options
    parser = OptionParser()
    parser.add_option('--config', dest='config_file', default=CONFIG_FILE, help='Config file')
    options, _ = parser.parse_args()

    # get config, merge with default values
    try:
        conf = yaml.load(open(options.config_file))
    except:
        die('failed to load config from %s' % options.config_file)

    # This kludge is used, because pymongo has problems with connecting to IPv6 hosts by hostname
    # Convert hostnames to IP addresses. IPv6 is preferred
    for srv, srv_opts in conf['servers'].items():
        ip = host2ip(srv_opts['host'])
        if ip:
            srv_opts['host'] = ip
        else:
            die('Can not convert hostname %s to neither iPv6 nor IPv4' % srv_opts['host'])
    for cfgsrv, cfgsrv_opts in conf['config_servers'].items():
        ip = host2ip(cfgsrv_opts['host'])
        if ip:
            cfgsrv_opts['host'] = ip
        else:
            die('Can not convert hostname %s to neither iPv6 nor IPv4' % cfgsrv_opts['host'])

    # check rsync and mongodump exist in path
    p = Popen('which rsync', shell=True, stdout=PIPE)
    rsync_path, _ = p.communicate()
    rsync_path = rsync_path.replace('\n','')
    if p.returncode != 0:
        die('rsync not found in PATH')
    p = Popen('which mongodump', shell=True, stdout=PIPE)
    mongodump_path, _ = p.communicate()
    mongodump_path = mongodump_path.replace('\n','')
    if p.returncode != 0:
        die('mongodump not found in PATH')

    # try to connect to any of config servers

    cfg_client = None
    for cfgsrv, cfgsrv_opts in conf['config_servers'].items():
        try:
            logging.info('Connecting to config server %s' % cfgsrv)
            cfg_client = pymongo.MongoClient(host=cfgsrv_opts['host'], port=cfgsrv_opts['port'])
            if cfgsrv_opts['user'] and cfgsrv_opts['password']:
                cfg_client[cfgsrv_opts['db']].authenticate(cfgsrv_opts['user'], cfgsrv_opts['password'])
        except Exception, e:
            logging.error('Failed to connect: %s' % str(e))
            cfg_client.close()
            cfg_client = None
        else:
            logging.info('Connected')
            break
    if cfg_client is None:
        die('Failed to connect to any of config servers')

    # check if Balancer is not running, exit if it is
    logging.info('Check if balancer is running')
    balancerStopped = False
    try:
        balancerStopped = cfg_client.config.settings.find_one({'_id':'balancer'})['stopped']
    except Exception, e:
        die('Failed to check if balamcer is running: %s' % str(e))
    if not balancerStopped:
        die('Balancer is not stopped - can not make backup')
    else:
        cfg_client.close()

    # connect to every mongod
    clients = {}
    for srv, srv_opts in conf['servers'].items():
        try:
            logging.info('Connecting to server %s' % srv)
            clients[srv] = pymongo.MongoClient(host=srv_opts['host'], port=srv_opts['port'])
            if srv_opts['user'] and srv_opts['password']:
                clients[srv][srv_opts['db']].authenticate(srv_opts['user'], srv_opts['password'])
        except Exception, e:
            die('Failed to connect to server %s' % srv)
        else:
            logging.info('Connected')

    # lock all servers
    for name, client in clients.items():
        try:
            logging.info('Trying to lock server %s' % name)
            client.admin.command('fsync', lock=True)
        except:
            logging.error('Failed to lock server %s' % name)
            logging.info('Try to unlock all already locked clients')
            for _, c in clients:
                try:
                    if c.is_locked:
                        c.unlock()
                except:
                    pass
            die('Failed to lock all servers')

    # run rsync in background
    rsync_args = [rsync_path] + [opt for opt in conf['rsync_options']] + \
                 [v['dir'] for _, v in conf['servers'].items()] + [conf['backup_dir']]
    rsync_args = map(str, rsync_args)
    logging.info('Running rsync: ' + pformat(rsync_args))
    rsync_proc = Popen(rsync_args, stdin=None)

    # get dump of config server
    mongodump_args = [mongodump_path] + [opt for opt in conf['mongodump_options']]
    # klugde with replace().replace() : mongo api want ipv6 address enclosed in [], bug mongodump doesn't
    mongodump_args += ['--host', cfgsrv_opts['host'].replace('[', '').replace(']', '')]
    mongodump_args += ['--port', cfgsrv_opts['port']]
    if cfgsrv_opts['user']:
        mongodump_args += ['--username', cfgsrv_opts['user']]
    if cfgsrv_opts['password']:
        mongodump_args += ['-p%s' % cfgsrv_opts['password']]
    mongodump_args += ['--out', '%s/configsvr' % conf['backup_dir']]
    mongodump_args = map(str, mongodump_args)

    logging.info('Running mongodump: ' + pformat(mongodump_args))
    mongodump_failed = False
    mongodump_process = Popen(mongodump_args)
    mongodump_process.wait()
    if mongodump_process.returncode != 0:
        logging.error('Error: rsync finished with return code %d' %  mongodump_process.returncode)
        logging.info('Trying to stop rsync')
        rsync_proc.terminate()
        mongodump_failed = True

    # wait for rsync to finish
    rsync_proc.wait()
    rsync_failed = False
    if rsync_proc.returncode != 0:
        logging.error('Error: rsync finished with return code %d' % rsync_proc.returncode)
        rsync_failed = True

    # Try to unlock all servers
    for name, client in clients.items():
        try:
            logging.info('Trying to unlock client %s' % name)
            client.unlock()
            client.close()
        except Exception, e:
            logging.error('Failed to unlock client %s: %s' % (name, str(e)))

    if mongodump_failed:
        die('mongodump failed')
    elif rsync_failed:
        die('rsync failed')

    # Finish
    try:
        open(conf['backup_ok'], 'w+').write('')
    except:
        die('Backup fihished, but can not write to file %s' % conf['backup_ok'])
    else:
        die('Backup fihished', exit_code=0)
