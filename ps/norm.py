#!/usr/bin/env python

import sys
import argparse
import psconfig
import pandas as pd

cfg = psconfig.PSConfig()

parser = argparse.ArgumentParser(description="Summarize performance data", fromfile_prefix_chars='@')

parser.add_argument("base", help="Base file")
parser.add_argument("input", help="Input file")
parser.add_argument("-m", dest="metric", help="Metric to normalize")
parser.add_argument("-k", dest="key", action="append", default=['experiment'])
parser.add_argument("--rk", dest="right_keys", action="append", default=[], help="Retain right keys")
parser.add_argument("--rsuffix", dest="right_suffix", default="_right")
parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

t = pd.read_csv(args.input)
if len(args.key) == 1:
    args.key += cfg.get_key()

common_keys = set(args.key) & set(args.right_keys)
if common_keys != set():
    print >>sys.stderr, "Keys (%s) duplicated in join and in retain" % (", ".join(common_keys),)
    sys.exit(1)
    
t = pd.read_csv(args.input)
b = pd.read_csv(args.base)
m = t.merge(b[args.key + [args.metric] + args.right_keys], 'left', on=args.key, suffixes=('', args.right_suffix))
m[args.metric + "_norm"] = m[args.metric] / m[args.metric + "_right"]
m.to_csv(args.output,index=False)
