#!/usr/bin/env python
#
# collect.py
#
# Scans log files for "COLLECT" and outputs a list of files to be
# collected. Part of bmk2.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import sys
import datetime
import logproc
import argparse
import os

def build_collect_list(logfile, skip_failed = True, strip_path = 0, suffix = None):
    out = {}
    last_runid = {}
    failed_runids = set()

    basepath = ""
    for r in logproc.parse_log_file(logfile):
        if r.type == "COLLECT":
            if r.filetype == "basepath":
                basepath = r.file
            else:
                if r.rsid not in out:
                    out[r.rsid] = {}

                if r.runid not in out[r.rsid]:
                    out[r.rsid][r.runid] = {}

                last_runid[r.rsid] = r.runid

                if r.filetype not in out[r.rsid][r.runid]:
                    out[r.rsid][r.runid][r.filetype] = []

                s = strip_path
                x = -1
                n = r.file
                while s > 0:
                    x = r.file.find('/', x + 1)
                    if x == -1: break
                    s -= 1
                else:
                    n = r.file[x+1:]

                if suffix:
                    n = n + suffix

                out[r.rsid][r.runid][r.filetype].append(n)
        elif r.type == "FAIL":
            if "run failed" in r.message: # not robust!
                if r.binid in last_runid:
                    if skip_failed:
                        del out[r.binid][last_runid[r.binid]]

    return basepath, out

def add_names(fnames, basepath, files, out):
    added_fnames = []
    added_out = []

    for f in files:
        if os.path.basename(f) in fnames:
            print >>sys.stderr, "ERROR: duplicate", os.path.basename(f)
            sys.exit(1)

        bn = os.path.basename(f)
        fp = os.path.join(basepath, f)

        fnames.add(bn)
        out.append(fp)

        added_fnames.append(bn)
        added_out.append(fp)

    return added_fnames, added_out

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Collect extra files generated during test2.py in a single directory")
    parser.add_argument('logfile', help='Logfile')
    parser.add_argument('filetype', nargs='?', help='Type of files to collect (default: all)', default=[])
    parser.add_argument('-p', dest="strip_path", type=int, metavar='NUM', help='Strip NUM components from filename before combining with basepath', default=0)
    parser.add_argument('-m', dest="map", metavar='FILE', help='Store map of RSID, file and filetype in FILE', default=None)
    parser.add_argument("-a", dest='append', action='store_true', default=False, help="Append to map file")
    parser.add_argument('-s', dest="suffix", metavar='SUFFIX', help='Add suffix to filename', default=0)
    parser.add_argument('--collect-failed', dest="skip_failed", action="store_false", default=True, help='Collect files from failed runs')

    args = parser.parse_args()

    basepath, colfiles = build_collect_list(args.logfile, args.skip_failed, args.strip_path, args.suffix)
    out = []
    fnames = set()
    revmap = {}
    for rsid in colfiles:
        for runid in colfiles[rsid]:
            for ft in colfiles[rsid][runid]:
                if len(args.filetype) and ft in args.filetype:
                    af, ao = add_names(fnames, basepath, colfiles[rsid][runid][ft], out)
                elif len(args.filetype) == 0:
                    af, ao = add_names(fnames, basepath, colfiles[rsid][runid][ft], out)

                for f, ff in zip(af, ao):
                    revmap[f] = (rsid, runid, ft, ff)
                
    assert len(fnames) == len(out)
    print "\n".join(out)

    if args.map:
        mapfile = open(args.map, "w" if not args.append else "a")
        if mapfile:
            for fn in fnames:
                x = revmap[fn]
                print >>mapfile, "%s %s %s %s %s" % (x[0], x[1], x[2], fn, x[3])

