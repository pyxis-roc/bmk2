#!/usr/bin/env python

import sys
import ConfigParser
import argparse
from extras import *
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)-10s %(message)s')

p = argparse.ArgumentParser("Run conversion binaries")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--bispec", dest="bispec", metavar="FILE_OR_MNEMONIC", help="Binary+Input specification")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")

args = p.parse_args()

loaded = standard_loader(args.metadir, args.inpproc, args.binspec, args.scan, args.bispec, bingroup='CONVERTERS')
if not loaded:
    sys.exit(1)
else:
    basepath, binspecs, l = loaded

rspecs = l.get_run_specs()
#rspecs.sort(key=lambda x: x.bid)

for rs in rspecs:
    print rs
