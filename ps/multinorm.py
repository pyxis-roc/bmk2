#!/usr/bin/env python
#
# norm.py
#
# Normalizes performance data, part of bmk2/ps.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import sys
import argparse
import psconfig
import pandas as pd

cfg = psconfig.PSConfig()

parser = argparse.ArgumentParser(description="Normalize performance data by joining input and base on keys and calculating input[metric] / base[metric] ", fromfile_prefix_chars='@')

parser.add_argument("base", help="Base file")
parser.add_argument("inputs", nargs="+", help="Input files")
parser.add_argument("-l", dest="lbl", help="Input labels", action="append", default=[])
parser.add_argument("-m", dest="metric", action="append", help="Metric to normalize", default=[])
parser.add_argument("-k", dest="key", action="append", default=[])
parser.add_argument("-s", dest="suffix", default="_norm", help="Suffix for result")
parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

if len(args.key) == 0:
    args.key += cfg.get_key()

assert len(args.metric)

b = pd.read_csv(args.base, index_col=args.key)
if len(b) == 0:
    print >>sys.stderr, "ERROR: %s does not contain any records" % (args.base,)
    sys.exit(1)

out = pd.DataFrame()
out[args.metric] = b[args.metric]
out["experiment"] = b["experiment"]

assert len(args.lbl) == len(args.inputs), "Number of labels (-l, %d) does not match number of inputs (%d)" % (len(args.lbl), len(args.inputs))

data_cols = dict([(v, []) for v in args.metric])
for i, l in zip(args.inputs, args.lbl):
    t = pd.read_csv(i, index_col=args.key)
    if len(t) == 0:
        print >>sys.stderr, "ERROR: %s does not contain any records" % (i,)
        sys.exit(1)

    for am in args.metric:
        cn = am + "_" + l
        data_cols[am].append(cn)
        out[cn] = t[am]

    out["experiment_" + l] = t["experiment"] # for sanity checking, could also be filename?

for m in data_cols:
    ocl = [x + args.suffix for x in data_cols[m]]
    for c, oc  in zip(data_cols[m],  ocl):
        out[oc] = out[c] / out[m]
        
    out2 = out.dropna()

    print out2[ocl].describe()


out.to_csv(args.output)
