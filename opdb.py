#
# opdb.py
#
# Object properties database for bmk2.  Sections in CFG files indicate
# objects, section keys indicate properties.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import ConfigParser
from collections import OrderedDict

def cfg_get(fn, section, key, default=None):
    try:
        v = fn(section, key)
        return v
    except ConfigParser.NoOptionError:
        return default

class ObjectProps(object):
    pass

class ObjectPropsCFG(ObjectProps):
    """Read/Write a .cfg file as a object property file.
    
       Sections names indicate objects, section keys indicate properties."""

    def __init__(self, filename, fmt, acceptable_versions):
        self.filename = filename
        self.fmt = fmt
        self.acceptable_versions = acceptable_versions
        self.meta = None
        self.objects = OrderedDict()

    def check_version(self, version):
        return version in self.acceptable_versions

    def update_props(self, props):
        return props

    def parse_section(self, cfg, section): 
        d = OrderedDict(cfg.items(section))
        d = self.update_props(d)
        return d

    def unparse_section(self, section):
        return section
    
    def post_load(self):
        return True

    def load(self):
        x = ConfigParser.SafeConfigParser()

        out = OrderedDict()
        with open(self.filename, "rb") as f:
            x.readfp(f)

            v = cfg_get(x.get, self.fmt, "version")

            self.version = v

            if not self.check_version(v):
                av = [str(v) for v in self.acceptable_versions]
                if v:
                    print >>sys.stderr, "Unknown version: %s (acceptable: %s)" % (v, ", ".join(av))
                else:
                    print >>sys.stderr, "Unable to determine version (acceptable: %s)" % (", ".join(av))
                
            for s in x.sections():
                if s == self.fmt:
                    self.meta = self.parse_section(x, s)
                else:
                    if s in out:
                        print >>sys.stderr, "Warning: Duplicate section '%s', overwriting" % (s,)

                    out[s] = self.parse_section(x, s)

            self.objects = out
            return self.post_load()

        return False

    def save(self, fn = None):
        def write_items(cfg, section, items):
            for k, v in items.iteritems():
                cfg.set(section, k, v)

        x = ConfigParser.SafeConfigParser()
        
        assert self.filename or fn, "Both filename and fn cannot be empty."
        if not fn: fn = self.filename

        x.add_section(self.fmt)
        write_items(x, self.fmt, self.unparse_section(self.meta))

        for s in self.objects:
            x.add_section(s)
            write_items(x, s, self.unparse_section(self.objects[s]))

        with open(fn, "wb") as f:
            x.write(f)
        
    def __iter__(self):
        return iter(self.objects.itervalues())
