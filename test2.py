#!/usr/bin/env python

import sys
import argparse
import os
import bmk2
import logging
import datetime

TIME_FMT = "%Y-%m-%d %H:%M:%S"

def do_run(args, rspecs):
    log.info("SYSTEM: %s" % (",".join(os.uname())))
    log.info("DATE START %s" % (datetime.datetime.now().strftime(TIME_FMT)))

    for rs in rspecs:
        x = rs.run()
        rsid = rs.get_id()

        if x.run_ok:
            if args.verbose:
                if x.stdout: log.info(x.stdout)
                if x.stderr: log.info(x.stderr)

            if rs.checker.check(x):
                log.log(PASS_LEVEL, "%s: %s" % (rsid, x))
                x.cleanup()
            else:
                log.log(FAIL_LEVEL, "%s: check failed: %s" % (rsid, x))
                if args.fail_fast:
                    sys.exit(1)
        else:
            log.log(FAIL_LEVEL, "%s: run failed" % (rsid))
            if r.stdout: log.info("%s STDOUT\n" %(rsid) + r.stdout)
            if r.stderr: log.info("%s STDERR\n" %(rsid) + r.stderr + "%s END\n" % (rsid))
            x.cleanup()
            if args.fail_fast:
                sys.exit(1)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

FAIL_LEVEL = logging.getLevelName("ERROR") + 1
PASS_LEVEL = logging.getLevelName("ERROR") + 2
logging.addLevelName(FAIL_LEVEL, "FAIL")
logging.addLevelName(PASS_LEVEL, "PASS")

p = argparse.ArgumentParser("Run tests")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")

sp = p.add_subparsers(help="sub-command help", dest="command")
plist = sp.add_parser('list', help="List runspecs")
plist.add_argument('binputs', nargs='*', help="Limit to binaries and/or inputs")
plist.add_argument('--show-files', action="store_true", help="Limit to binaries and/or inputs", default=False)

prun = sp.add_parser('run', help="Run binaries")
prun.add_argument('binputs', nargs='*', help="List of binaries and/or inputs to execute")
prun.add_argument('--ff', dest="fail_fast", action="store_true", help="Fail fast", default=False)
prun.add_argument('-v', "--verbose", dest="verbose", action="store_true", help="Show stdout and stderr of program", default=False)

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
rspecs.sort(key=lambda x: x.bid)
checks = [rs.check() for rs in rspecs]

if not all(checks):
    log.info("Some checks failed. See previous error messages for information.")
    sys.exit(1)

log.info("Configuration loaded successfully.")

if args.command == "list":
    prev_bid = None
    for rs in rspecs:
        if rs.bid != prev_bid:
            print rs.bid
            prev_bid = rs.bid

        print "\t", rs.input_name
        if args.show_files:
            files = rs.get_input_files() +rs.checker.get_input_files()
            print "\t\t", " ".join(files)

elif args.command == "run":
    do_run(args, rspecs)


