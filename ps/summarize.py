#!/usr/bin/env python

import sys
import argparse
import psconfig
import pandas as pd

def select(group, skey):
    if args.pick == 'min':
        idx = group[args.metric].argmin()
    elif args.pick == 'max':
        idx = group[args.metric].argmax()
    else:
        assert False
    
    d = {}
    for k in group:
        if k in skey: 
            continue

        d[k] = group[k].loc[idx] #group.loc[idx].to_dict()
    
    return pd.DataFrame(d, index=[0])

cfg = psconfig.PSConfig()

parser = argparse.ArgumentParser(description="Summarize performance data", fromfile_prefix_chars='@')

parser.add_argument("input", help="Input file")
parser.add_argument("-m", dest="metric", help="Metric to summarize")
parser.add_argument("-k", dest="key", action="append", default=['experiment'])
parser.add_argument("-p", dest="pick", choices=['min', 'max'], default='min')
parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

t = pd.read_csv(args.input)
if len(args.key) == 1:
    args.key += cfg.get_key()
    
skey = set(args.key)

t = pd.read_csv(args.input)
tg = t.groupby(args.key)
x = tg.apply(select, skey)
x.reset_index(len(skey), drop=True,inplace=True)
x.to_csv(args.output)
