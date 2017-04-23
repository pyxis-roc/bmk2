#!/usr/bin/env python

import pandas as pd
import argparse
import math

def critlevel(n, level_perc):
    import scipy.stats

    # not the same alpha as in the eqns ...
    alpha = level_perc / 100.0

    if n > 32:
        return scipy.stats.norm.interval(alpha)[1]
    else:
        return scipy.stats.t.interval(alpha, n - 1)[1]

def calc_ci(stdev, n, level_perc):
    t1 = critlevel(n, level_perc)
    se = stdev / math.sqrt(n)
    zt = t1*se
    
    return zt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate confidence intervals")
    parser.add_argument("average", help="Average", type=float)
    parser.add_argument("stdev", help="Standard deviation", type=float)
    parser.add_argument("n", help="Sample size", type=float)
    parser.add_argument("--level", help="Level in percentage", type=float, default=95)

    args = parser.parse_args()
    zt = calc_ci(args.stdev, args.n, args.level)
    print "%0.2f &plusmn; %0.2f" % (args.average, zt)
