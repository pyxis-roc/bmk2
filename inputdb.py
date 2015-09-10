#!/usr/bin/env python

import sys
import os
import ConfigParser
import argparse
import common
import fnmatch
import inputprops
from core import Input
from opdb import ObjectPropsCFG

class InputDBcfg(ObjectPropsCFG):
    def __init__(self, filename, inpproc = None, bt = None):
        super(InputDBcfg, self).__init__(filename, "bmktest2", ["2"])
        self.inpproc = inpproc
        self.bt = bt

        self.unserialize_input = None
        self.serialize_input = None

        if self.inpproc:
            inpproc = common.load_py_module(self.inpproc)
            if 'unserialize_input' in inpproc:
                self.unserialize_input = inpproc['unserialize_input']

            if 'serialize_input' in inpproc:
                self.serialize_input = inpproc['serialize_input']                

    def init(self, basepath):
        self.meta = dict([('version', "2"), ('basepath', basepath)])

    def post_load(self):
        if self.bt is not None:
            self.bt.update(self.meta)

        basepath = self.meta['basepath']

        for s in self.objects:
            e = self.objects[s]
            if self.unserialize_input:
                e = self.unserialize_input(e, basepath)

                e['file'] = os.path.join(basepath, e['file'])

        return True

    def unparse_section(self, section):
        if self.serialize_input:
            self.serialize_input(section)

        if 'file' in section:
            l = len(self.meta['basepath']) 
            if section['file'][:l] == self.meta['basepath']:
                section['file'] = section['file'][l+1:]


        return section

class InputDB(object):
    def __init__(self, cfgfile, inpproc = None, inputprops = None):
        self.cfg = cfgfile
        self.inpproc = inpproc
        self.inputprops = inputprops
        self.inputdb_cfg = InputDBcfg(self.cfg, self.inpproc, {})

    def get_alt_format(self, name, fmt):
        if name in self.n2i:
            for x in self.n2i[name]:
                if x.props.format == fmt:
                    return x

    def load(self):
        if not self.inputdb_cfg.load():
            print >>sys.stderr, "Unable to load!"
            return False

        bt = self.inputdb_cfg.bt

        if self.inputprops is not None:
            # not .props as Properties!
            self.props = inputprops.read_prop_file(self.inputprops, bt)
            inputprops.apply_props(self.inputdb, self.props)

        self.inputdb = [Input(i, self) for i in self.inputdb_cfg]
        self.inpnames = set([i.get_id() for i in self.inputdb])

        self.n2i = dict([(n, list()) for n in self.inpnames])
        for i in self.inputdb:
            self.n2i[i.get_id()].append(i)

    def __iter__(self):
        return iter(self.inputdb)
       
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Prepare an inputs database")
    p.add_argument("--glob", help="Glob")
    p.add_argument("--update", action="store_true", help="Update dbfile")
    p.add_argument("inpproc", help="Input processor (python module)")
    p.add_argument("dbfile", help="Output database file")
    p.add_argument("basepath", nargs="?", help="Scan this path for inputs", default=".")
    
    args = p.parse_args()
    inpproc = common.load_py_module(args.inpproc)

    if args.update:
        idb = InputDB(args.dbfile, args.inpproc)
        idb.load()
        basepath = idb.inputdb_cfg.meta['basepath']
        print >>sys.stderr, "using basepath from file: %s" % (basepath,)
    else:
        idb = InputDB(args.dbfile, args.inpproc)
        basepath = args.basepath
        idb.inputdb_cfg.init(basepath)

    describe_input = inpproc['describe_input']

    out = []
    for root, dirnames, filenames in os.walk(basepath):
        rp = os.path.relpath(root, basepath)
        
        if args.glob:
            filenames = fnmatch.filter(filenames, args.glob)       

        for f in filenames:
            x = describe_input(root, f, rp)
            if x:
                x['file'] = os.path.join(rp, f)
                if x['file'] not in idb.inputdb_cfg.objects:
                    print >>sys.stderr, x['file']
                    idb.inputdb_cfg.objects[x['file']] = x

    if args.update:
        #TODO: check for basepath changes
        idb.inputdb_cfg.save(args.dbfile + ".update")
    else:
        idb.inputdb_cfg.save(args.dbfile)

