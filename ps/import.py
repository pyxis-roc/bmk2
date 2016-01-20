#!/usr/bin/env python

import sys
import argparse
import psconfig
import pandas as pd

def check_raw_data(raw_table):
    rdtable = raw_table
    counts = {}

    err = False

    present = set()
    for r in rdtable[['xid', 'run']].itertuples(index=False):
        if r in present:
            print >>sys.stderr, "ERROR: Possibly duplicate raw data: xid: %s run: %d" % (r[0],r[1])
            err = True
    
        present.add(r)

        xid = r[0]
        
        if xid not in counts:
            counts[xid] = 0

        counts[xid] += 1

    for xid, count in counts.iteritems():
        if count == 1:
            print >>sys.stderr, "WARNING: Only one raw data point for %s" % (xid,)

    return not err

def average_data(key, raw_table, fields_to_avg):
    def avg(group):
        assert len(group) > 0

        kv = tuple([group[k].iloc[0] for k in key])
        xids = set(group['xid'])
        if len(xids) > 1:
            print >>sys.stderr, "Multiple XIDs for key '%s' in average_data: xid: %s" % (kv, group['xid'].iloc[0])
        
        out = {'xid': [group['xid'].iloc[0]]}
        
        for c in fields_to_avg:
            if c in group:
                out[c + '_avg'] = [group[c].mean()]
                out[c + '_sd'] = [group[c].std()]
                out[c + '_count'] = [len(group)]
                out[c + '_sum'] = [group[c].sum()]
            
        return pd.DataFrame(out)

    rtg = raw_table[key + ['xid'] + fields_to_avg].groupby(key, sort=False)
    rtga = rtg.apply(avg)
    rtga.reset_index(len(key), drop=True, inplace=True)  # drop the index of the dataframe that is returned by apply
    return rtga

cfg = psconfig.PSConfig()

parser = argparse.ArgumentParser(description="Import raw performance data")

parser.add_argument("input", help="Input file")

parser.add_argument("-o", dest="output", metavar="FILE", 
                    default="/dev/stdout", help="Output file")

args = parser.parse_args()

t = pd.read_csv(args.input)
key = ['experiment'] + cfg.get_key()
t.sort_values(by=key, inplace=True)

if check_raw_data(t):
    avg_fields = cfg.get('import', 'average', None)
    if avg_fields is None:
        print >>sys.stderr, "Could not find list of fields to average (import.average) in configuration"
        sys.exit(1)

    x = average_data(key, t, ['time_ns'])
    x.to_csv(args.output, reset_index=True)
    if len(x) == 0:
        print >>sys.stderr, "WARNING: No records were imported!"
        sys.exit(1)

