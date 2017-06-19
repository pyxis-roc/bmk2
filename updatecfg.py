#!/usr/bin/env python

import ConfigParser
import argparse
import sys


p = argparse.ArgumentParser(description="Merge two configuration files")
p.add_argument("src1", help="Original source")
p.add_argument("src2", help="Merge file")
p.add_argument("output", nargs="?", help="Output file")

args = p.parse_args()

s1 = ConfigParser.RawConfigParser()
s1.readfp(open(args.src1, "r"))

s2 = ConfigParser.RawConfigParser()
s1.readfp(open(args.src2, "r"))

for s in s2.sections():
    if not s1.has_section(s):
        print >> sys.stderr, "Section '%s' does not exist in original" % (s,)
        continue

    for n, v in s2.items(s):
        s1.set(s, n, v)

if args.output:
    of = open(args.output, "w")
else:
    of = sys.stdout

s1.write(of)
