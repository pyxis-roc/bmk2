#!/usr/bin/env python

import re
import datetime
from collections import namedtuple

sdate = namedtuple("sdate", ['type', 'start_date'])
edate = namedtuple("edate", ['type', 'end_date'])

run_begin = namedtuple("run_begin", ['type', 'begin'])
run_end = namedtuple("run_end", ['type', 'end'])

perf_info = namedtuple('perf_info', ['type', 'binid', 'xid', 'run', 'time_ns', 'cmdline'])

missing_info = namedtuple('missing_info', ['type', 'binid'])

st = re.compile("^START")
dt = re.compile("^INFO DATE (START|END)")
pd_begin = re.compile("^INFO PERFDATE BEGIN_RUN")
pd_end = re.compile("^INFO PERFDATE END_RUN")
p = re.compile("^PERF ")
missing = re.compile("^FAIL MISSING PERF")

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
