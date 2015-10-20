#!/usr/bin/env python

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

        if dp.st_dev != dnp.st_dev:
            return None

        d = dn
        dp = dnp


class PSConfig(object):
    def __init__(self, cfg = None):
        self.cfg = cfg
        if cfg is None:
            self.cfg = autolocate_config()

        self._cfg = ConfigParser.SafeConfigParser()

        if self.cfg:
            self._cfg.readfp(open(self.cfg, "r"))
        else:
            self._cfg.set('bmk2ps', 'ver', '2')

        self._key = None
        self._binid_re = None

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
                k = [kk[0] for k in k]
        else:
            k = [kk.strip() for kk in k.split(",")]

        if k is None:
            k = ['binid']

        self._key = k
        return self._key

    def version(self):
        return self.get('bmk2ps', 'ver')

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
