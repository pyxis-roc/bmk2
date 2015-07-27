#!/usr/bin/env python

import sys
import argparse
import os
import bmk2
import logging
import datetime
import time
from extras import *

TIME_FMT = "%Y-%m-%d %H:%M:%S"

def std_run(args, rs):
    rsid = rs.get_id()
    x = rs.run()

    if x.run_ok:
        if args.verbose:
            if x.stdout: log.info(x.stdout)
            if x.stderr: log.info(x.stderr)

        if rs.checker.check(x):
            log.log(PASS_LEVEL, "%s: %s" % (rsid, x))
            x.cleanup()
            return True, x
        else:
            log.log(FAIL_LEVEL, "%s: check failed: %s" % (rsid, x))
            return False, x
    else:
        log.log(FAIL_LEVEL, "%s: run failed" % (rsid))
        if x.stdout: log.info("%s STDOUT\n" %(rsid) + x.stdout)
        if x.stderr: log.info("%s STDERR\n" %(rsid) + x.stderr + "%s END\n" % (rsid))
        x.cleanup()
        return False, x
    
def do_run(args, rspecs):
    log.info("SYSTEM: %s" % (",".join(os.uname())))
    log.info("DATE START %s" % (datetime.datetime.now().strftime(TIME_FMT)))

    for rs in rspecs:
        rsid = rs.get_id()

        run_ok, x = std_run(args, rs)
        if not run_ok and args.fail_fast:
            sys.exit(1)

def do_perf(args, rspecs):
    runid_base = str(time.time()) # this should really be a nonce
    runid = 0

    for rs in rspecs:
        rsid = rs.get_id()
        run = 0
        repeat = 0
        runid += 1

        while run < args.repeat:
            ts = datetime.datetime.now()
            log.info("PERFDATE BEGIN_RUN %s" % (ts.strftime(TIME_FMT)))
            run_ok, x = std_run(args, rs)
            log.info("PERFDATE END_RUN %s" % (datetime.datetime.now().strftime(TIME_FMT)))
            runid_c = runid_base + "." + str(runid)

            if run_ok:
                p = rs.perf.get_perf(x)
                if p is None:
                    log.log(FAIL_LEVEL, "%s: perf extraction failed: %s" % (rsid, x))
                    if args.fail_fast:
                        sys.exit(1)
                    else:
                        break

                # TODO: delay this until we have all repeats?
                log.log(PERF_LEVEL, "%s %s %s %s %s" % (rsid, runid_c, run, p['time_ns'], x))
                run += 1
            else:
                if repeat < 3:
                    log.log(FAIL_LEVEL, "%s %s: failed, re-running: %s" % (rsid, runid_c, x))
                    repeat += 1
                else:
                    if run == 0:
                        # we never managed to run this ...
                        log.log(FAIL_LEVEL, "MISSING PERF %s" % (rsid,))

                    if args.fail_fast:
                        sys.exit(1)

                    break

log = logging.getLogger(__name__)

FAIL_LEVEL = logging.getLevelName("ERROR") + 1
PASS_LEVEL = logging.getLevelName("ERROR") + 2
PERF_LEVEL = logging.getLevelName("ERROR") + 3

logging.addLevelName(FAIL_LEVEL, "FAIL")
logging.addLevelName(PASS_LEVEL, "PASS")
logging.addLevelName(PERF_LEVEL, "PERF")

p = argparse.ArgumentParser("Run tests")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")
p.add_argument("--log", dest="log", metavar="FILE", help="Store logs in FILE")
p.add_argument('-v', "--verbose", dest="verbose", action="store_true", help="Show stdout and stderr of executing programs", default=False)

sp = p.add_subparsers(help="sub-command help", dest="command")
plist = sp.add_parser('list', help="List runspecs")
plist.add_argument('binputs', nargs='*', help="Limit to binaries and/or inputs")
plist.add_argument('--show-files', action="store_true", help="Limit to binaries and/or inputs", default=False)

prun = sp.add_parser('run', help="Run binaries")
prun.add_argument('binputs', nargs='*', help="List of binaries and/or inputs to execute")
prun.add_argument('--ff', dest="fail_fast", action="store_true", help="Fail fast", default=False)

pperf = sp.add_parser('perf', help="Run performance tests")
pperf.add_argument('binputs', nargs='*', help="List of binaries and/or inputs to execute")
pperf.add_argument('--ff', dest="fail_fast", action="store_true", help="Fail fast", default=False)
pperf.add_argument('-r', dest="repeat", metavar="N", type=int, help="Number of repetitions", default=3)

args = p.parse_args()

if args.log:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s', filename=args.log, filemode='wb') # note the 'wb', instead of 'a'
    console = logging.StreamHandler()
    fmt = logging.Formatter('%(levelname)-8s %(name)-10s %(message)s')
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logging.getLogger('').addHandler(console)
else:
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)-10s %(message)s')

if args.scan:
    binspecs = scan(args.scan, "bmktest2.py")
else:
    if not os.path.exists(args.binspec):
        print >>sys.stderr, "Unable to find %s" % (args.binspec,)
    binspecs = [args.binspec]

l = bmk2.Loader(args.metadir, args.inpproc)
if not l.initialize(): sys.exit(1)

sel_inputs, sel_binaries = l.split_binputs(args.binputs)

sys.path.append(args.metadir)
if not l.load_multiple_binaries(binspecs, sel_binaries): sys.exit(1)
if not l.associate_inputs(sel_inputs): sys.exit(1)

rspecs = l.get_run_specs()
rspecs.sort(key=lambda x: x.bid)
checks = [rs.check() for rs in rspecs]

if not all(checks):
    log.info("Some checks failed. See previous error messages for information.")
    sys.exit(1)

log.info("Configuration loaded successfully.")

start = datetime.datetime.now()
log.info("SYSTEM: %s" % (",".join(os.uname())))
log.info("DATE START %s" % (start.strftime(TIME_FMT)))

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
    summarize(log, rspecs)
elif args.command == "perf":
    do_perf(args, rspecs)
    summarize(log, rspecs)

end = datetime.datetime.now()
log.info("DATE END %s" % (end.strftime(TIME_FMT)))
log.info("APPROXIMATE DURATION %s" % (end - start)) # modulo clock adjusting, etc.
logging.shutdown()
