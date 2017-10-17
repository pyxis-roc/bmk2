#!/usr/bin/env python

import argparse
import glob
import os

def site_init(metadir, site):
    sf = glob.glob(os.path.join(metadir, "SITE-IS.*"))

    if len(sf) > 0:
        print >>sys.stderr, "ERROR: Sitefiles exist: '%s'" % (sf,)
        return 0

    f = open(os.path.join(metadir, "SITE-IS.%s" % (site,)), "w")
    f.close()

def dispatch_site(args):
    if args.cmd == "init":
        if args.site is None:
            print >>sys.stderr, "ERROR: site init requires -s site option"
        else:
            site_init(args.metadir, args.site)


p = argparse.ArgumentParser(description="Setup a bmk2 configuration directory")
p.add_argument("-d", dest="metadir", help="Path to use as bmk2 configuration directory", default=".")

sp = p.add_subparsers(dest="subcommand")

sc = sp.add_parser('site', help="Site initialization")
sc.add_argument("cmd", choices=["init"])
sc.add_argument("-s", dest="site", help="Site to use")

args = p.parse_args()

if args.subcommand == "site":
    dispatch_site(args)
else:
    pass
