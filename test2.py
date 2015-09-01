#!/usr/bin/env python

import sys
import argparse
import os
import bmk2
import logging
import datetime
import time
from extras import *
import logproc
import overlays
import config
import core
import resource

TIME_FMT = "%Y-%m-%d %H:%M:%S"

def load_rlimits(lo):
    x = core.RLimit()
    rlimit_cpu = lo.config.get_var("rlimit.cpu", None)
    if rlimit_cpu is not None:        
        log.info('Setting RLIMIT_CPU to %s' % (rlimit_cpu,))
        x.setrlimit(resource.RLIMIT_CPU, (int(rlimit_cpu), int(rlimit_cpu)))

    return x

def read_log(logfiles):
    if not isinstance(logfiles, list):
        logfiles = [logfiles]

    binids = set()
    for l in logfiles:
        for r in logproc.parse_log_file(l):
            if r.type == "TASK_COMPLETE":
                binids.add(r.rsid)

    return binids

def std_run(args, rs, runid):
    rsid = rs.get_id()
    x = rs.run(runid)

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
    log.info("TASK run")

    xid_base = str(time.time()) # this should really be a nonce
    runid = 0
    for rs in rspecs:
        rsid = rs.get_id()
        xid_c = xid_base + "." + str(runid)
        runid += 1

        run_ok, x = std_run(args, rs, xid_c) # in this case because we do not repeat, xid_c == runid
        if not run_ok and args.fail_fast:
            sys.exit(1)
        
        if run_ok:
            log.log(TASK_COMPLETE_LEVEL, "%s RUN" % (rsid,))
            
def do_perf(args, rspecs):
    log.info("TASK perf")
    xid_base = str(time.time()) # this should really be a nonce
    runid = 0

    for rs in rspecs:
        rsid = rs.get_id()
        run = 0
        repeat = 0
        runid += 1

        while run < args.repeat:
            xid_c = xid_base + "." + str(runid)

            ts = datetime.datetime.now()
            log.info("PERFDATE BEGIN_RUN %s" % (ts.strftime(TIME_FMT)))
            run_ok, x = std_run(args, rs, xid_c + "." + str(run + repeat))
            log.info("PERFDATE END_RUN %s" % (datetime.datetime.now().strftime(TIME_FMT)))

            if run_ok:
                p = rs.perf.get_perf(x)
                if p is None:
                    log.log(FAIL_LEVEL, "%s: perf extraction failed: %s" % (rsid, x))
                    if args.fail_fast:
                        sys.exit(1)
                    else:
                        break

                # TODO: delay this until we have all repeats?
                log.log(PERF_LEVEL, "%s %s %s %s %s" % (rsid, xid_c, run, p['time_ns'], x))
                run += 1
            else:
                if repeat < 3:
                    log.log(FAIL_LEVEL, "%s %s: failed, re-running: %s" % (rsid, xid_c, x))
                    repeat += 1
                else:
                    if run == 0:
                        # we never managed to run this ...
                        log.log(FAIL_LEVEL, "MISSING PERF %s" % (rsid,))
                    else:
                        log.log(TASK_COMPLETE_LEVEL, "%s PERF %d/%d/%d" % (rsid, run, repeat, args.repeat))

                    if args.fail_fast:
                        sys.exit(1)

                    break

def check_rspecs(rspecs):
    checks = []
    out = []
    all_ok = True

    for rs in rspecs:
        x = rs.check()
        if not x:
            if args.ignore_missing_binaries and len(rs.errors) == 1 and 'missing-binary' in rs.errors:
                # do not add rs to out [and do not pass go.]
                all_ok = False
                continue

        checks.append(x)
        out.append(rs)

    return all_ok, checks, out

log = logging.getLogger(__name__)

FAIL_LEVEL = logging.getLevelName("ERROR") + 1
PASS_LEVEL = logging.getLevelName("ERROR") + 2
PERF_LEVEL = logging.getLevelName("ERROR") + 3
COLLECT_LEVEL = logging.getLevelName("ERROR") + 4
TASK_COMPLETE_LEVEL = logging.getLevelName("ERROR") + 5

logging.addLevelName(FAIL_LEVEL, "FAIL")
logging.addLevelName(PASS_LEVEL, "PASS")
logging.addLevelName(PERF_LEVEL, "PERF")
logging.addLevelName(COLLECT_LEVEL, "COLLECT")
logging.addLevelName(TASK_COMPLETE_LEVEL, "TASK_COMPLETE")

p = argparse.ArgumentParser("Run tests")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--bispec", dest="bispec", metavar="FILE_OR_MNEMONIC", help="Binary+Input specification")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")
p.add_argument("--log", dest="log", metavar="FILE", help="Store logs in FILE")
p.add_argument("--ignore-missing-binaries", action="store_true", default = False)
p.add_argument("--cuda-profile", dest="cuda_profile", action="store_true", help="Enable CUDA profiling")
p.add_argument("--cp-cfg", dest="cuda_profile_config", metavar="FILE", help="CUDA Profiler configuration")
p.add_argument("--cp-log", dest="cuda_profile_log", action="store_true", help="CUDA Profiler logfile", default="cp_{rsid}_{runid}.log")

p.add_argument("--nvprof", dest="nvprof", action="store_true", help="Enable CUDA profiling via NVPROF")
p.add_argument("--nvp-metrics", dest="nvp_metrics", help="Comma-separated list of NVPROF metrics")

p.add_argument("--read", dest="readlog", metavar="FILE", help="Read previous log")
p.add_argument('-v', "--verbose", dest="verbose", action="store_true", help="Show stdout and stderr of executing programs", default=False)
p.add_argument('--missing', dest="missing", action="store_true", help="Select new/missing runspecs")

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

PREV_BINIDS = set()
if args.readlog:
    assert args.readlog != args.log
    PREV_BINIDS = read_log(args.readlog)

if args.log:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(message)s', filename=args.log, filemode='wb') # note the 'wb', instead of 'a'
    console = logging.StreamHandler()
    fmt = logging.Formatter('%(levelname)-8s %(name)-10s %(message)s')
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logging.getLogger('').addHandler(console)
else:
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)-10s %(message)s')


if args.readlog:
    log.info('%d completed task rsids read from log' % (len(PREV_BINIDS)))

if args.scan:
    basepath = os.path.abspath(args.scan)
    binspecs = scan(args.scan, "bmktest2.py")
else:
    if not os.path.exists(args.binspec):
        print >>sys.stderr, "Unable to find %s" % (args.binspec,)

    basepath = os.path.abspath(".")
    binspecs = [args.binspec]

l = bmk2.Loader(args.metadir, args.inpproc)
ftf = {}
if args.bispec:
    f = None
    if os.path.exists(args.bispec) and os.path.isfile(args.bispec):
        f = args.bispec
    else:
        f = l.config.get_var("bispec_" + args.bispec, None)
        f = os.path.join(args.metadir, f)

    assert f is not None, "Unable to find file or spec in config file for bispec '%s'" % (args.bispec,)
    ftf[config.FT_BISPEC] = f

if not l.initialize(ftf): sys.exit(1)
sel_inputs, sel_binaries = l.split_binputs(args.binputs)

sys.path.append(args.metadir)
if not l.load_multiple_binaries(binspecs, sel_binaries) and not args.ignore_missing_binaries: sys.exit(1)
if not l.associate_inputs(sel_inputs): sys.exit(1)

rspecs = l.get_run_specs()
rspecs.sort(key=lambda x: x.bid)

all_ok, checks, rspecs = check_rspecs(rspecs)

if not all(checks):
    log.info("Some checks failed. See previous error messages for information.")
    sys.exit(1)

if all_ok:
    log.info("Configuration loaded successfully.")
else:
    log.info("Configuration loaded with some errors ignored. See previous error messages for information.")

start = datetime.datetime.now()
log.info("SYSTEM: %s" % (",".join(os.uname())))
log.info("DATE START %s" % (start.strftime(TIME_FMT)))
log.log(COLLECT_LEVEL, "basepath %s" % (basepath,))

if args.missing:
    rspecs = filter(lambda rs: rs.get_id() not in PREV_BINIDS, rspecs)

if args.cuda_profile:
    cp_cfg_file = args.cuda_profile_config or l.config.get_var("cp_cfg", None)
    cp_log_file = args.cuda_profile_log or l.config.get_var("cp_log", None)

    if cp_cfg_file:
        assert os.path.exists(cp_cfg_file) and os.path.isfile(cp_cfg_file), "CUDA Profiler Config '%s' does not exist or is not a file" % (cp_cfg_file,)

    overlays.add_overlay(rspecs, overlays.CUDAProfilerOverlay, profile_cfg=cp_cfg_file, profile_log=cp_log_file)
elif args.nvprof:
    cp_log_file = args.cuda_profile_log or l.config.get_var("cp_log", None)
    overlays.add_overlay(rspecs, overlays.NVProfOverlay, profile_cfg="--metrics %s" % (args.nvp_metrics), profile_log=cp_log_file)

tmpdir = l.config.get_var("tmpdir", None)
if tmpdir: 
    assert (os.path.exists(tmpdir) and os.path.isdir(tmpdir)), "Temporary directory '%s' does not exist or is not a directory" % (tmpdir,)
    overlays.add_overlay(rspecs, overlays.TmpDirOverlay, tmpdir)
    for r in rspecs:
        r.set_tmpdir(tmpdir)

rl = load_rlimits(l)

for r in rspecs:
    r.set_rlimit(rl)

if args.command == "list":
    prev_bid = None
    for rs in rspecs:
        if rs.bid != prev_bid:
            print rs.bid,
            prev_bid = rs.bid
            if rs.bid in l.config.disable_binaries:
                print "\t** DISABLED **",
            print

        print "\t", rs.input_name
        if args.show_files:
            files = rs.get_input_files() +rs.checker.get_input_files()
            print "\t\t", " ".join(files)
elif args.command == "run":
    for b in l.config.disable_binaries:
        log.info("DISABLED BINARY %s" % (b,))

    rspecs = [rs for rs in rspecs if rs.bid not in l.config.disable_binaries]
    do_run(args, rspecs)
elif args.command == "perf":
    for b in l.config.disable_binaries:
        log.info("DISABLED BINARY %s" % (b,))

    rspecs = [rs for rs in rspecs if rs.bid not in l.config.disable_binaries]
    do_perf(args, rspecs)

summarize(log, rspecs)    
end = datetime.datetime.now()
log.info("DATE END %s" % (end.strftime(TIME_FMT)))
log.info("APPROXIMATE DURATION %s" % (end - start)) # modulo clock adjusting, etc.
logging.shutdown()
