#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import os
from datetime import datetime, timedelta


# Get core root content
root = os.path.dirname(os.path.realpath(__file__))
configFile = os.path.join(root, 'config.ini')


_cfg = None
_timestamp = None


def _getCfgObject():
    ''' Read with caching feature the config file '''
    global _timestamp
    global _cfg

    if _timestamp is None:
        _timestamp = datetime.now()

    change = False

    # Check changes
    if _cfg is None:
        change = True
    if datetime.now() - _timestamp > timedelta(minutes = 120):
        change = True

    # Apply changes
    if change is True:
        cfg = configparser.ConfigParser()
        cfg.read(configFile)
        _cfg = cfg

    return _cfg



def getCfg(group, value, dataType='str'):
    ''' Get config file data '''
    cfg = _getCfgObject()
    configuration = cfg.get('APPLICATION', 'configuration')

    # Place here the group you want to skip -DEBUG or -RELEASE mode
    skipped = ['APPLICATION']

    # Setting to upper case
    if configuration is not None:
        if group not in skipped:
            configuration = configuration.upper()
            group = group + '-' + configuration

    if dataType == 'str':
        return cfg.get(group, value)
    elif dataType == 'int':
        return cfg.getint(group, value)
    elif dataType == 'float':
        return cfg.getfloat(group, value)
    elif dataType == 'boolean':
        return cfg.getboolean(group, value)
    else:
        return cfg.get(group, value)


def isRelease():
    ''' Check if system is in release mode or not '''
    cfg = _getCfgObject()
    configuration = cfg.get('APPLICATION', 'configuration')
    return (configuration == 'RELEASE')

def isDebug():
    ''' Check if system is in debug mode or not '''
    cfg = _getCfgObject()
    configuration = cfg.get('APPLICATION', 'configuration')
    return (configuration == 'DEBUG')


if __name__ == '__main__':
    # Try to read one value
    print getCfg('MYSQL', 'host')
