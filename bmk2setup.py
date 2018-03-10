#!/usr/bin/env python

import argparse
import glob
import os
import sys

def site_init(metadir, site):
    sf = glob.glob(os.path.join(metadir, "SITE-IS.*"))

    if len(sf) > 0:
        print >>sys.stderr, "ERROR: Sitefiles exist: '%s'" % (sf,)
        return 0

    f = open(os.path.join(metadir, "SITE-IS.%s" % (site,)), "w")
    f.close()

def config_setup(metadir, system):
    if not os.path.exists(metadir) or not os.path.isdir(metadir):
        print >>sys.stderr, "ERROR: %s does not exist or is not a directory" % (metadir,)
        return 0

    tmpl = [("bmk2.cfg", """
[bmk2]
version=2
inputdb={system}.inputdb
inputprops={system}.inputprops
bispec={system}.bispec
#disable_binaries=
    
#[default-config]
#configvar=value
"""),
    ("{system}.inputdb",
     """[bmktest2]
version=2
basepath=./inputs
     """),
    ("{system}.inputprops","""
[bmktest2-props]
version=2
    """),
    ("{system}.bispec","""#v1
#binary inputs
""")]

    for cfgfile, _ in tmpl:
        cf = os.path.join(metadir, cfgfile.format(system=system))
        if os.path.exists(cf):
            print >>sys.stderr, "ERROR: File '%s' already exists" % (cf,)
            return 0

    for cfgfile, tmpldata in tmpl:
        cf = os.path.join(metadir, cfgfile.format(system=system))
        if not os.path.exists(cf):
            with open(cf, "w") as f:
                f.write(tmpldata.format(system = system))

    return 1

def dispatch_site(args):
    if args.cmd == "init":
        if args.site is None:
            print >>sys.stderr, "ERROR: site init requires -s site option"
        else:
            site_init(args.metadir, args.site)

def dispatch_config(args):
    if args.cmd == "setup":
        if args.project is None:
            print >>sys.stderr, "ERROR: config setup requires -p project option"
        else:
            config_setup(args.metadir, args.project)

p = argparse.ArgumentParser(description="Setup a bmk2 configuration directory")
p.add_argument("-d", dest="metadir", help="Path to use as bmk2 configuration directory", default=".")

sp = p.add_subparsers(dest="subcommand")

sc = sp.add_parser('site', help="Site initialization")
sc.add_argument("cmd", choices=["init"])
sc.add_argument("-s", dest="site", help="Site to use")

scfg = sp.add_parser('config', help="Config initialization")
scfg.add_argument("cmd", choices=["setup"])
scfg.add_argument("-p", dest="project", help="Short project name (suitable as a filename)")

args = p.parse_args()

if args.subcommand == "site":
    dispatch_site(args)
elif args.subcommand == "config":
    dispatch_config(args)
else:
    pass
