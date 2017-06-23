#!/usr/bin/env python
# measure_energy.py
#
# Measure energy on Intel platforms that support RAPL access through
# the powercap interface.
#
# Part of bmk2
#
# Copyright (c) 2017 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>


import sys
import os
import subprocess
import glob

def get_rapl_files():
    dom = glob.glob("/sys/class/powercap/intel-rapl:*")
    
    out = {}
    for d in dom:
        dd = os.path.basename(d)
        f = os.path.join(d, "energy_uj")
        if os.path.exists(f):
            out[dd] = f

    return out

def read_rapl_power(rapl_files):
    out = {}
    for k, f in rapl_files.items():
        of = open(f, "r")
        out[k] = int(of.read())
        of.close()

    return out

def calc_power(bef, aft):
    out = {}
    for k in bef:
        out[k] = aft[k] - bef[k]

    return out

if len(sys.argv) == 1:
    print >>sys.stderr, "Usage: %s cmd-line\n" % (sys.argv[0],)
    exit(1)

cmdline = sys.argv[1:]

rf = get_rapl_files()
if len(rf):
    bef = read_rapl_power(rf)
    subprocess.check_call(cmdline)
    aft = read_rapl_power(rf)
    p = calc_power(bef, aft)
    for k in p:
        print "INSTR", k, p[k] # micro joules
else:
    print >>sys.stderr, "Did not find RAPL power counters (/sys/class/powercap/intel-rapl*)"
    sys.exit(1)
