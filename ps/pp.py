#!/usr/bin/env python

import pandas as pd
import argparse
import psconfig

def add_ci(d, level_perc, field = 'time_ns'):
    import numpy
    import scipy.stats

    def critlevel():
        # not the same alpha as in the eqns ...
        alpha = level_perc / 100.0

        def x(n):
            if n > 32:
                return scipy.stats.norm.interval(alpha)[1]
            else:
                return scipy.stats.t.interval(alpha, n - 1)[1]

        return x

    t1 = d["%s_count" % (field,)].apply(critlevel())
    se = d["%s_sd" % (field,)] / numpy.sqrt(d["%s_count" % (field,)])

    zt = t1*se
    
    d["%s_avg" %(field,) + "_ci%d" % (level_perc,)] = zt    

def prettify(fmt, i, r, unit = 'ms', keys = ['experiment', 'binid', 'input']):

    x = {}
    for j, k in enumerate(keys):
        x[k] = i[j]

    t = "time_" + unit

    x['time'] = r[t + "_avg"]
    x['sd'] = r[t + "_sd"]

    x['ci95'] = r["time_ns_avg_ci95"]
    if unit == 'ms':
        x['ci95'] /= 1E6

    x['unit'] = unit
    x['runs'] = r["time_ns_count"]

    return fmt.format(**x)

    #return "%s/%s/%s " % i + "%0.2f ms (s.d. %0.2f ms) +- %0.2f ms" % (r['time_ms_avg'], r['time_ms_sd'], r['time_ns_avg_ci95'] / 1E6)

cfg = psconfig.PSConfig()
parser = argparse.ArgumentParser(description="Pretty print performance numbers")
parser.add_argument("csvfile", nargs="+", help="csvfiles after import")
parser.add_argument("--fmt", help="format", default="{experiment} {binid}/{input} {time:0.2f} +- {ci95:0.2f} {unit}  s.d. {sd:0.2f} ms runs {runs}")

args = parser.parse_args()
k = ['experiment'] + cfg.get_key()
for f in args.csvfile:
    df = pd.read_csv(f, index_col = k)

    add_ci(df, 95)

    df["time_ms_avg"] = df["time_ns_avg"] / 1E6
    df["time_ms_sd"] = df["time_ns_sd"] / 1E6

    for i, r in df.iterrows():
        print prettify(args.fmt, i, r, keys=k)
