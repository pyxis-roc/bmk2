#!/usr/bin/env python

import sys
import inputdb
import argparse
import ConfigParser
import os

def apply_props(inputdb, props):
    for e in inputdb:
        if e['name'] in props:
            e.update(props[e['name']])

    return True

def read_prop_file(propfile, inputdb_bt):
    x = ConfigParser.SafeConfigParser()

    basepath = inputdb_bt['basepath']

    out = []
    with open(propfile, "rb") as f:
        x.readfp(f)

        v = x.getint("bmktest2-props", "version")
        if v != 2:
            printf >>sys.stderr, "Unknown version: %s" % (v,)
            return None

        try:
            path_items = x.get("bmktest2-props", "paths")
            path_items = set([xx.strip() for xx in path_items.split(",")])
        except ConfigParser.NoOptionError:
            path_items = set()
        
        for s in x.sections():
            if s == "bmktest2-props": 
                continue

            e = dict(x.items(s))

            for pi in path_items:
                if pi in e:
                    e[pi] = os.path.join(basepath, e[pi])

            out.append((s, e)) # TODO: duplicate sections?

    return dict(out)    

if __name__ == "__main__":
    p = argparse.ArgumentParser("Create an input properties file")
    p.add_argument("inputdb", help="Inputdb file")
    p.add_argument("inputprops", help="Inputprops file")

    args = p.parse_args()

    names = set()
    bt = {}
    x = inputdb.read_cfg_file(args.inputdb, bmktest2 = bt)
    cfg = ConfigParser.SafeConfigParser()

    cfg.add_section('bmktest2-props')
    cfg.set('bmktest2-props', 'version', bt['version'])

    for e in x:
        nm = e['name']

        if nm not in names:
            cfg.add_section(nm)
            cfg.set(nm, "name", nm)
            names.add(nm)

    with open(args.inputprops, "wb") as f:
        cfg.write(f)
