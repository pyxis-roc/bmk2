#!/usr/bin/env python

import sys
import argparse
import os
import bmk2
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

p = argparse.ArgumentParser("Run tests")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")

sp = p.add_subparsers(help="sub-command help", dest="command")
plist = sp.add_parser('list', help="List runspecs")
plist.add_argument('binputs', nargs='*', help="Limit to binaries and/or inputs")

prun = sp.add_parser('run', help="Run binaries")
prun.add_argument('binputs', nargs='*', help="List of binaries and/or inputs to execute")

args = p.parse_args()

if not os.path.exists(args.binspec):
    print >>sys.stderr, "Unable to find %s" % (args.binspec,)

l = bmk2.Loader(args.metadir, args.inpproc)
if not l.initialize(): sys.exit(1)

sel_inputs, sel_binaries = l.split_binputs(args.binputs)

sys.path.append(args.metadir)
if not l.load_binaries(args.binspec, sel_binaries): sys.exit(1)
if not l.associate_inputs(sel_inputs): sys.exit(1)

rspecs = l.get_run_specs()
checks = [rs.check() for rs in rspecs]
if not all(checks):
    log.info("Some checks failed. See previous error messages for information.")
    sys.exit(1)

log.info("Configuration loaded successfully.")

if args.command == "list":
    rspecs.sort(key=lambda x: x.bid)
    prev_bid = None
    for rs in rspecs:
        if rs.bid != prev_bid:
            print rs.bid
            prev_bid = rs.bid

        print "\t", rs.input_name


            #     for rs in rspecs:
            #         x = rs.run()
            #         print str(x)
            #         print x.stdout
            #         print x.retval
            #         if rs.checker.check(x):
            #             print "PASS"
            # else:

