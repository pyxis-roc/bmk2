#!/usr/bin/env python

import argparse
import glob
import os
import psconfig
import sys

def bmk2ps_init():
    c = psconfig.PSConfig()

    if os.path.exists('bmk2ps.cfg'):
        print >>sys.stderr, "ERROR: bmk2ps.cfg already exists"
        sys.exit(1)

    with open('bmk2ps.cfg', 'w') as f:
        c._cfg.write(f)

def dispatch_init(args):
    if args.subcommand == "init":
        bmk2ps_init()

p = argparse.ArgumentParser(description="Setup a bmk2 performance scripts configuration")

sp = p.add_subparsers(dest="subcommand")
sp.add_parser('init')

args = p.parse_args()

if args.subcommand == "init":
    dispatch_init(args)
else:
    pass
