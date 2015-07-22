#!/usr/bin/env python

import sys
import argparse
import os
import bmk2

p = argparse.ArgumentParser("Run tests")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to look for bispec and inputdb files", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")

p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")

args = p.parse_args()

if not os.path.exists(args.binspec):
    print >>sys.stderr, "Unable to find %s" % (args.binspec,)


l = bmk2.Loader(args.metadir, args.inpproc)
if l.initialize():
    sys.path.append(args.metadir)
    if l.load_binaries(args.binspec):
        if l.associate_inputs():
            checks = [rs.check() for rs in l.get_run_specs()]
            if all(checks):
                print "READY-TO-GO"
            else:
                print "Some checks failed. See previous error messages for information."


