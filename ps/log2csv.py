#!/usr/bin/env python
#
# log2csv.py
#
# Converts bmk2 perf log files into csv files, part of bmk2/ps.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import csv
import sys
import re
import argparse
import datetime
import bmk2.logproc
import bmk2.collect
import psconfig
import os

def fix_xid(record, fixed_xids):
    import zlib

    xid = record['xid']
    p = xid.find(".")
    if p == -1: return  # not in format we expect, return
    if xid[p-6:p-4] == "00" and len(xid) > 10: return # already fixed

    if xid in fixed_xids:
        record['xid'] = fixed_xids[xid]
        return
    
    discriminator = "%s|%s" % (record['time_ns'], record['cmdline'])
    val = str(zlib.adler32(discriminator) & 0xffffffff)
    if len(val) < 4: val = val + "0" * (4 - len(val))

    record['xid'] = record['xid'][:p] + "11" + val[:4] + record['xid'][p:]
    fixed_xids[xid] = record['xid']
    
def process_instr(name, v):
    if name == "ATOMICS":
        n = v.split()
        assert len(n) == 3
        n = sum(map(int, n))
        return str(n)
    elif "atomic_density_" in name:
        #print v
        return v
    elif "intel-rapl" in name:        
        return v
    elif "gpu_memory_" in name:
        return v
    else:
        assert False, name


cfg = psconfig.PSConfig()

TIME_FMT = "%Y-%m-%d %H:%M:%S"

parser = argparse.ArgumentParser(description="Extract performance date from a log file to a CSV")

parser.add_argument("input", nargs="+", help="Input file")

parser.add_argument("--fix-xid", action="store_true", help="Deterministically extend xid from old bmk2 versions to avoid collisions")

parser.add_argument("--add-missing", action="store_true", help="Add missing records")

parser.add_argument("-x", dest="experiment", metavar="FILE", help="Experiment name")

parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

#parser.add_argument("-s", dest="suite", help="Suite")

args = parser.parse_args()



mix = {}
if args.experiment:
    mix['experiment'] = args.experiment


binid_re = cfg.get_binid_re()

if binid_re:
    hdr = sorted(binid_re.groupindex.iteritems(), key=lambda x: x[1])
    hdr = [h[0] for h in hdr]
else:
    binid_re = re.compile(r"(?P<binid>.+)/(?P<input>[^/]+)")
    hdr = ["binid", "input"]

START_DATE = None
END_DATE = None

instr = {}
rows = []
total_time = None
add_keys = set()
fixed_xids = {}
for i in args.input:
    basepath, collogs = bmk2.collect.build_collect_list(i) # TODO: avoid this 2-time parsing ...

    for r in bmk2.logproc.parse_log_file(i):
        if r.type == "START_DATE":
            START_DATE = r.start_date
            mix["date_exp"] = r.start_date
        elif r.type == "END_DATE":
            END_DATE = r.end_date
            if total_time:
                total_time += datetime.datetime.strptime(END_DATE, TIME_FMT) - datetime.datetime.strptime(START_DATE, TIME_FMT)
            else:
                total_time = datetime.datetime.strptime(END_DATE, TIME_FMT) - datetime.datetime.strptime(START_DATE, TIME_FMT)
        elif r.type == "RUN_BEGIN":
            instr = {}
            mix["date_run_begin"] = r.begin
        elif r.type == "RUN_END":
            mix["date_run_end"] = r.end
        elif r.type == "PERF":
            out = {}
            #out['bmk'], out['variant'], out['input'] = r.binid.split("/")
            if binid_re:
                m = binid_re.match(r.binid)
                out.update(m.groupdict())
            else:
                out['binid'] = r.binid

            out['xid'] = r.xid
            out['run'] = r.run
            out['time_ns'] = r.time_ns
            out['cmdline'] = r.cmdline

            if args.fix_xid:
                fix_xid(out, fixed_xids)

            if r.binid in collogs:
                runid = r.xid + "." + r.run
                if runid in collogs[r.binid]:
                    for ft in collogs[r.binid][runid]:
                        add_keys.add(ft)
                        out[ft] = ";".join([os.path.join(basepath, x) for x in collogs[r.binid][runid][ft]]) # WARNING: ; should not be in filename

            if mix:
                out.update(mix)

            for k, v in instr.iteritems():
                out["instr_" + k.lower()] = process_instr(k, v)

            rows.append(out)
        elif r.type == "MISSING":
            print >>sys.stderr, "MISSING", r.binid
            if args.add_missing:
                out = {}
                if binid_re:
                    m = binid_re.match(r.binid)
                    out.update(m.groupdict())
                else:
                    out['binid'] = r.binid

                # this is from the last record
                if mix:
                    out.update(mix)
                
                rows.append(out)
        elif r.type == "COLLECT":
            pass
        elif r.type == "INSTR":
            assert r.name not in instr, instr
            instr[r.name] = r.args
            add_keys.add('instr_' + r.name.lower())
        elif r.type == "TASK_COMPLETE":            
            instr = {}
        elif r.type == "FAIL":
            pass
        else:
            assert False, r.type

fieldnames = hdr + ['xid', 'run', 'time_ns', 'date_run_begin', 'date_run_end', 'date_exp', 'cmdline'] + list(add_keys)
if args.experiment:
    fieldnames.insert(0, 'experiment')

ocsv = csv.DictWriter(open(args.output, "w"), fieldnames)
ocsv.writeheader()
ocsv.writerows(rows)

logfiles = " ".join(args.input)

if len(rows) == 0:
    print >>sys.stderr, "WARNING: Log files (%s) did not contain perf numbers!" % (logfiles,)
    sys.exit(1)

if total_time is not None:
    print >>sys.stderr, "Total time for experiment (h:m:s)", total_time
else:
    if END_DATE is None:
        print >>sys.stderr, "%s: WARNING: no DATE END found, log file (%s) was probably incomplete." % (args.logfiles,)
        sys.exit(1)
    else:
        print >>sys.stderr, "WARNING: unable to calculate total time for experiment, possibly malformed logfiles (%s)!" % (args.logfiles,)
        # do not return an error?
        sys.exit(1)
