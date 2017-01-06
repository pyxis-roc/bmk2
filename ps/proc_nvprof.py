#!/usr/bin/env python

import npreader2
import npreader2.pdutils
import argparse
import bmk2.mapfile
import os
import pandas as pd
import psconfig
import sys

cfg = psconfig.PSConfig()

p = argparse.ArgumentParser(description="Process nvprof files")
p.add_argument("mapfile", help="Mapfile")
p.add_argument("output", nargs="?", help="Output")
p.add_argument("-d", dest="dir", help="Data directory containing all NVPROF files")
p.add_argument("-x", dest="experiment", help="Add experiment field")
p.add_argument("-c", dest="columns", action="append", help="Append", default=[])

args = p.parse_args()

binid_re = cfg.get_binid_re()
if binid_re:
    hdr = sorted(binid_re.groupindex.iteritems(), key=lambda x: x[1])
    hdr = [h[0] for h in hdr]
else:
    binid_re = re.compile(r"(?P<binid>.+)/(?P<input>[^/]+)")
    hdr = ["binid", "input"]

out = pd.DataFrame()

for me in bmk2.mapfile.read_mapfile(args.mapfile):
    if me.filetype != "cuda/nvprof":
        continue

    print >>sys.stderr, me.filename

    if args.dir:
        nvp = os.path.join(args.dir, me.filename)
    else:
        nvp = me.abspath
        
    db = npreader2.NVProfile(nvp)
    df = npreader2.pdutils.kernels2df(db, demangle=True, shorten=True)
   
    df = df.reset_index()
    df.set_index(['name', 'invocation'], inplace=True)

    cols = ['duration_ns'] + args.columns

    cc = {}
    for c in cols:
        cc[c] = {}
        for fn in ["sum", "count"]:
            cc[c][c + "_" + fn] = fn

    oe = df.groupby(level='name')[cols].agg(cc)
    assert me.input != ""
    binpid = "%s/%s" % (me.binid, me.input)
    m = binid_re.match(binpid)

    for k in hdr:
        oe[k] = m.group(k)

    oe['xid'], oe['run'] = bmk2.mapfile.split_runid(me.runid)

    if args.experiment:
        oe['experiment'] = args.experiment

    oe = oe.reset_index()
    oe = oe.set_index(hdr + ['name', 'xid'])
    out = out.append(oe)

if args.output:
    outfile = args.output
else:
    outfile = sys.stdout

out.to_csv(outfile)
