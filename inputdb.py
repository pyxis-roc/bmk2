#!/usr/bin/env python

import sys
import os
import ConfigParser
import argparse
import common

def read_cfg_file(cfgfile, inpproc = None):
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
            if s == "bmktest2": continue

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
    p.add_argument("inpproc", help="Input processor (python module)")
    p.add_argument("dbfile", help="Output database file")
    p.add_argument("basepath", nargs="?", help="Scan this path for inputs", default=".")
    
    args = p.parse_args()
    inpproc = common.load_py_module(args.inpproc)

    describe_input = inpproc['describe_input']

    basepath = args.basepath
    dbfile = args.dbfile

    out = []
    for root, dirnames, filenames in os.walk(basepath):
        rp = os.path.relpath(root, basepath)
        for f in filenames:
            x = describe_input(root, f, rp)
            if x:
                x['file'] = os.path.join(rp, f)
                out.append(x)

    write_cfg_file(dbfile, basepath, out)

