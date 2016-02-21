#!/usr/bin/env python
#
# bmk2info.py
#
# Dump information from bmktest2.py files (such as benchmark input
# files, checker input files, etc.).
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import sys
import ConfigParser
import argparse
from extras import *
import logging
import opdb
import os
import re
import sconvert

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)-10s %(message)s')

p = argparse.ArgumentParser("Generate conversion makefile")
p.add_argument("output", nargs="?", default="/dev/stdout")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--bispec", dest="bispec", metavar="FILE_OR_MNEMONIC", help="Binary+Input specification")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")
p.add_argument("-v", dest="verbose", type=int, help="Verbosity", default=0)
p.add_argument("-i", dest="include", action="append", default=[], choices=set(['inputs', 'checker-inputs', 'all']))

args = p.parse_args()

if len(args.include) == 0 or "all" in args.include:
    args.include = ['inputs', 'checker-inputs']

args.include = set(args.include)

loaded = standard_loader(args.metadir, args.inpproc, args.binspec, args.scan, args.bispec)
if not loaded:
    sys.exit(1)
else:
    basepath, binspecs, l = loaded

out = []
rspecs = l.get_run_specs()
for rs in rspecs:
    if "inputs" in args.include:
        out += [(rs.input_name, f) for f in rs.get_input_files()]

    if "checker-inputs" in args.include:
        out += [(rs.input_name, f) for f in rs.checker.get_input_files()]

out = list(set(out))

for e in out:
    print "%s %s" % e
