#!/usr/bin/env python

import re
import datetime
from collections import namedtuple

sdate = namedtuple("sdate", ['type', 'start_date'])
edate = namedtuple("edate", ['type', 'end_date'])

# note: rsid and binid are one and the same
run_begin = namedtuple("run_begin", ['type', 'begin'])
run_end = namedtuple("run_end", ['type', 'end'])
collect_entry = namedtuple("collect_entry", ['type', 'rsid', 'runid', 'filetype', 'file'])
perf_info = namedtuple('perf_info', ['type', 'binid', 'xid', 'run', 'time_ns', 'cmdline'])
tc_info = namedtuple('tc_info', ['type', 'rsid', 'task', 'task_args'])
missing_info = namedtuple('missing_info', ['type', 'binid'])

st = re.compile("^START")
dt = re.compile("^INFO DATE (START|END)")
collect_bp = re.compile("^COLLECT basepath (.*)$")
collect = re.compile("^COLLECT (.*) (.*) (.*) (.*)$")
pd_begin = re.compile("^INFO PERFDATE BEGIN_RUN")
pd_end = re.compile("^INFO PERFDATE END_RUN")
p = re.compile("^PERF ")
missing = re.compile("^FAIL MISSING PERF")
tc_re = re.compile("^TASK_COMPLETE ([^ ]+) ([^ ]+)( (.*))?$")

def parse_log_file(logfile):
    with open(logfile, "r") as f:
        for l in f:
            m = st.match(l)
            if m:
                assert False, l
                print m.group(0)
                continue

            m = dt.match(l)
            if m:
                # may yield multiple dates if log files are
                # concatenate

                if m.group(1) == "START":
                    yield sdate("START_DATE", l.strip().split(" ", 3)[-1])
                else:
                    yield edate("END_DATE", l.strip().split(" ", 3)[-1])
                continue

            m = pd_begin.match(l)
            if m:
                yield run_begin("RUN_BEGIN", l.strip().split(" ", 3)[-1])
                continue

            m = pd_end.match(l)
            if m:
                yield run_end("RUN_END", l.strip().split(" ", 3)[-1])
                continue

            m = collect_bp.match(l)
            if m:
                fi = m.group(1)

                yield collect_entry("COLLECT", rsid="", runid="", filetype="basepath", file=fi)
                continue

            m = collect.match(l)
            if m:
                rsid = m.group(1)
                runid = m.group(2)
                ty = m.group(3)
                fi = m.group(4)

                yield collect_entry("COLLECT", rsid=rsid, runid=runid, 
                                    filetype=ty, file=fi)
                continue

            m = p.match(l)
            if m:
                ls = l.strip().split(" ", 5)
                out = perf_info("PERF", 
                                binid = ls[1], 
                                xid = ls[2],
                                run = ls[3],
                                time_ns = ls[4],
                                cmdline = ls[5])

                yield out
                continue

            m = missing.match(l)
            if m:
                yield missing_info("MISSING", binid = l.strip().split()[-1])
                continue

            m = tc_re.match(l)
            if m:
                rsid = m.group(1)
                task = m.group(2).strip()
                task_args = m.group(4)

                yield tc_info("TASK_COMPLETE", rsid, task, task_args)
                continue

if __name__ == "__main__":
    import sys
    for r in parse_log_file(sys.argv[1]):
        print r
