#!/usr/bin/env python

import sys
import os
import ConfigParser
import argparse
import common
import fnmatch
import inputprops
from core import Input

class InputDB(object):
    def __init__(self, cfgfile, inpproc = None, inputprops = None):
        self.cfg = cfgfile
        self.inpproc = inpproc
        self.inputprops = inputprops

    def get_alt_format(self, name, fmt):
        if name in self.n2i:
            for x in self.n2i[name]:
                if x.props.format == fmt:
                    return x
        
    def load(self):
        bt = {}
        self.inputdb = read_cfg_file(self.cfg, self.inpproc, bt)

        if self.inputprops is not None:
            # not .props as Properties!
            self.props = inputprops.read_prop_file(self.inputprops, bt)
            inputprops.apply_props(self.inputdb, self.props)

        self.inputdb = [Input(i, self) for i in self.inputdb]
        self.inpnames = set([i.get_id() for i in self.inputdb])

        self.n2i = dict([(n, list()) for n in self.inpnames])
        for i in self.inputdb:
            self.n2i[i.get_id()].append(i)

    def __iter__(self):
        return iter(self.inputdb)

def read_cfg_file(cfgfile, inpproc = None, bmktest2 = None):
    unserialize_input = None

    if inpproc:
        inpproc = common.load_py_module(inpproc)
        if 'unserialize_input' in inpproc:
            unserialize_input = inpproc['unserialize_input']

    x = ConfigParser.SafeConfigParser()

    out = []
    with open(cfgfile, "rb") as f:
        x.readfp(f)

        v = x.getint("bmktest2", "version")
        if v != 2:
            printf >>sys.stderr, "Unknown version: %s" % (v,)
            return None

        basepath = x.get("bmktest2", "basepath")

        for s in x.sections():
            if s == "bmktest2": 
                if bmktest2 is not None:
                    bmktest2.update(x.items(s))

                continue

            e = dict(x.items(s))
            if unserialize_input:
                e = unserialize_input(e, basepath)

            e['file'] = os.path.join(basepath, e['file'])

            out.append(e)

    return out

def write_cfg_file(cfgfile, basepath, entries):
    x = ConfigParser.SafeConfigParser()
    
    x.add_section("bmktest2")
    x.set("bmktest2", "version", "2")
    x.set("bmktest2", "basepath", basepath)
    
    for e in entries:
        sec = e['file']
        x.add_section(sec)
        for p in e:
            x.set(sec, p, e[p])

    with open(cfgfile, 'wb') as f:
        x.write(f)
        
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Prepare an inputs database")
    p.add_argument("--glob", help="Glob")
    p.add_argument("--update", action="store_true", help="Update dbfile")
    p.add_argument("inpproc", help="Input processor (python module)")
    p.add_argument("dbfile", help="Output database file")
    p.add_argument("basepath", nargs="?", help="Scan this path for inputs", default=".")
    
    args = p.parse_args()
    inpproc = common.load_py_module(args.inpproc)

    existing_files = set()
    if args.update:
        idb = InputDB(args.dbfile, args.inpproc)
        idb.load()
        existing_files = [x.props.file for x in idb]
        
    print existing_files

    describe_input = inpproc['describe_input']

    basepath = args.basepath
    dbfile = args.dbfile

    out = []
    for root, dirnames, filenames in os.walk(basepath):
        rp = os.path.relpath(root, basepath)
        
        if args.glob:
            filenames = fnmatch.filter(filenames, args.glob)       

        for f in filenames:
            x = describe_input(root, f, rp)
            if x:
                x['file'] = os.path.join(rp, f)
                fp = os.path.join(basepath, x['file'])

                if fp not in existing_files:
                    print fp
                    out.append(x)


    if args.update:
        write_cfg_file(dbfile + ".update", basepath, out)
    else:
        write_cfg_file(dbfile, basepath, out)

