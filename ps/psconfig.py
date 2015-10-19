#!/usr/bin/env python

import ConfigParser
import os

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
