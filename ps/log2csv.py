#!/usr/bin/env python

import csv
import sys
import re
import argparse
import datetime
import bmk2.logproc
import bmk2.collect
import psconfig
import os

def process_instr(name, v):
    if name == "ATOMICS":
        n = v.split()
        assert len(n) == 3
        n = sum(map(int, n))
        return str(n)        
    else:
        assert False, v.name


cfg = psconfig.PSConfig()

TIME_FMT = "%Y-%m-%d %H:%M:%S"

parser = argparse.ArgumentParser(description="Extract performance date from a log file to a CSV")

parser.add_argument("input", nargs="+", help="Input file")

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
    hdr = ["binid"]

START_DATE = None
END_DATE = None

instr = {}
rows = []
total_time = None
add_keys = set()
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
        elif r.type == "COLLECT":
            pass
        elif r.type == "INSTR":
            assert r.name not in instr, instr
            instr[r.name] = r.args
            add_keys.add('instr_' + r.name.lower())
        elif r.type == "TASK_COMPLETE":            
            instr = {}
        else:
            assert False, r.type

fieldnames = hdr + ['xid', 'run', 'time_ns', 'date_run_begin', 'date_run_end', 'date_exp', 'cmdline'] + list(add_keys)
if args.experiment:
    fieldnames.insert(0, 'experiment')

ocsv = csv.DictWriter(open(args.output, "w"), fieldnames)
ocsv.writeheader()
ocsv.writerows(rows)

if len(rows) == 0:
    print >>sys.stderr, "WARNING: Log file did not contain perf numbers!"
    sys.exit(1)

print >>sys.stderr, "Total time for experiment (h:m:s)", total_time
