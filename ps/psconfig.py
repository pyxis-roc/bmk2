#!/usr/bin/env python
#
# psconfig.py
#
# Performance Scripts configuration reader for bmk2/ps.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import ConfigParser
import os
import re

def autolocate_config(start = None, fn = "bmk2ps.cfg"):
    if start is None:
        start = os.getcwd()

        
    d = start
    dp = os.stat(d)
    while True:
        if os.path.exists(os.path.join(d, fn)):
            return os.path.join(d, fn)
        
        # WARNING: does not follow symlinks!
        dn = os.path.normpath(os.path.join(d, ".."))
        dnp = os.stat(dn)

        if d == dn: # usually "/"
            return None
        
        if dp.st_dev != dnp.st_dev:
            return None

        d = dn
        dp = dnp


class PSConfig(object):
    def __init__(self, cfg = None):
        self.cfg = cfg
        if cfg is None:
            self.cfg = autolocate_config()

        self._cfg = ConfigParser.SafeConfigParser(allow_no_value=True)
        
        if self.cfg:
            self._cfg.readfp(open(self.cfg, "r"))
        else:
            self._cfg.add_section('bmk2ps')
            self._cfg.set('bmk2ps', 'ver', '2')
            self._cfg.add_section('data')
            self._cfg.set('data', '# key=binid,input')
            self._cfg.add_section('import')
            self._cfg.set('import', '# binid_decompose=re')
            self._cfg.set('import', '# average=field1,field2')


        self._key = None
        self._binid_re = None
        self._avg_fields = None

    def get_binid_re(self):
        if self._binid_re:
            return self._binid_re

        binid_re = self.get('import', 'binid_decompose')
        if binid_re:
            self._binid_re = re.compile(binid_re)
            
        return self._binid_re

    def get_key(self):
        if self._key:
            return self._key
        
        k = self.get('data', 'key')
        if k is None:
            binid_re = self.get_binid_re()
            if binid_re:
                k = sorted(binid_re.groupindex.iteritems(), key=lambda x: x[1])
                k = [kk[0] for kk in k]
        else:
            k = [kk.strip() for kk in k.split(",")]

        if k is None:
            k = ['binid', 'input']

        self._key = k
        return self._key

    def get_average_fields(self):
        if self._avg_fields:
            return self._avg_fields

        self._avg_fields = self.get_csl('import', 'average', [])
        return self._avg_fields
        

    def version(self):
        return self.get('bmk2ps', 'ver')

    def get_csl(self, section, var, default = None):
        v = self.get(section, var, None)

        if v is None:
            return default
        else:
            return [vv.strip() for vv in v.split(",")]        

    def get(self, section, var, default = None):
        try:
            x = self._cfg.get(section, var)
            return x
        except ConfigParser.NoSectionError:
            return default
        except ConfigParser.NoOptionError:
            return default

if __name__ == "__main__":
    print autolocate_config()
