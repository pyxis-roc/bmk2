#!/usr/bin/env python

import csv
import sys
import argparse
import psconfig
import pandas as pd


cfg = psconfig.PSConfig()

TIME_FMT = "%Y-%m-%d %H:%M:%S"

parser = argparse.ArgumentParser(description="Update a raw CSV file with an update csv file")

parser.add_argument("input", help="Input file")
parser.add_argument("update", help="Update file")

parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

inp = pd.read_csv(args.input)
upd = pd.read_csv(args.update)

key = cfg.get_key()
outkeys = set(upd[key].itertuples(False))

out = inp.iloc[[x not in outkeys for x in inp[key].itertuples(False)]]
x = pd.concat([out, upd])
x.to_csv(args.output,index=False)

print >>sys.stderr, "Dropped %d rows from input" % (len(out) - len(inp))
print >>sys.stderr, "Added %d rows from update" % (len(upd))
