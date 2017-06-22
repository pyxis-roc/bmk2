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
parser.add_argument("input", help="Input file")
parser.add_argument("-m", dest="metric", help="Metric to normalize")
parser.add_argument("-k", dest="key", action="append", default=[])
parser.add_argument("--rk", dest="right_keys", action="append", default=["experiment"], help="Retain right keys")
parser.add_argument("--rsuffix", dest="right_suffix", default="_right")
parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

t = pd.read_csv(args.input)
if len(args.key) == 0:
    args.key += cfg.get_key()

common_keys = set(args.key) & set(args.right_keys)
if common_keys != set():
    print >>sys.stderr, "Keys (%s) duplicated in join and in retain" % (", ".join(common_keys),)
    sys.exit(1)
    
t = pd.read_csv(args.input)
b = pd.read_csv(args.base)

if len(t) == 0:
    print >>sys.stderr, "ERROR: %s does not contain any records" % (args.input,)
    sys.exit(1)

if len(b) == 0:
    print >>sys.stderr, "ERROR: %s does not contain any records" % (args.base,)
    sys.exit(1)


#print b[args.key + [args.metric] + args.right_keys]
m = t.merge(b[args.key + [args.metric] + args.right_keys], 'left', on=args.key, suffixes=('', args.right_suffix))
m[args.metric + "_norm"] = m[args.metric] / m[args.metric + args.right_suffix]
m.to_csv(args.output,index=False)
