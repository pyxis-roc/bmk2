#!/usr/bin/env python

import sys
import datetime
import logproc
import argparse
import os

def build_collect_list(logfile):
    out = {}
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

                if r.filetype not in out[r.rsid][r.runid]:
                    out[r.rsid][r.runid][r.filetype] = []

                out[r.rsid][r.runid][r.filetype].append(r.file)

    return basepath, out

def add_names(fnames, basepath, files, out):
    for f in files:
        if os.path.basename(f) in fnames:
            print >>sys.stderr, "ERROR: duplicate", os.path.basename(f)
            sys.exit(1)

        fnames.add(os.path.basename(f))
        out.append(os.path.join(basepath, f))            

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Collect extra files generated during test2.py in a single directory")
    parser.add_argument('logfile', help='Logfile')
    parser.add_argument('filetype', nargs='?', help='Type of files to collect (default: all)', default=[])

    args = parser.parse_args()

    basepath, colfiles = build_collect_list(args.logfile)
    out = []
    fnames = set()

    for rsid in colfiles:
        for runid in colfiles[rsid]:
            for ft in colfiles[rsid][runid]:
                if len(args.filetype) and ft in args.filetype:
                    add_names(fnames, basepath, colfiles[rsid][runid][ft], out)
                elif len(args.filetype) == 0:
                    add_names(fnames, basepath, colfiles[rsid][runid][ft], out)

    assert len(fnames) == len(out)
    print "\n".join(out)

