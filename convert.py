#!/usr/bin/env python

import sys
import ConfigParser
import argparse
from extras import *
import logging
import opdb
import os
import re
import convgraph

def gen_xform_fn(srcname, dstname):
    src_re = re.compile(srcname)

    def f(s):
        return src_re.sub(dstname, s)

    return f

class ConvSpec(opdb.ObjectPropsCFG):
    pass

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(name)-10s %(message)s')

p = argparse.ArgumentParser("Run conversion binaries")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--bispec", dest="bispec", metavar="FILE_OR_MNEMONIC", help="Binary+Input specification")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")

args = p.parse_args()

loaded = standard_loader(args.metadir, args.inpproc, args.binspec, args.scan, args.bispec, bingroup='CONVERTERS')
if not loaded:
    sys.exit(1)
else:
    basepath, binspecs, l = loaded

convspec = l.config.get_var('convspec', None)
if not convspec:
    log.error("No 'convspec' in config file")
    sys.exit(1)

cs = ConvSpec(os.path.join(l.config.metadir, convspec), "bmk2-convspec", ["2"])
if not cs.load():
    log.error("Unable to read config file")
    sys.exit(1)

all_types = set()
conv = {}
for n, s in cs.objects.iteritems():    
    convgraph.register_conversion(s['src'], s['dst'], 
                                  gen_xform_fn(s['srcname'],
                                               s['dstname']))

    all_types.add(s['src'])
    all_types.add(s['dst'])

    conv[(s['src'], s['dst'])] = n

targets = []
out = []
rspecs = l.get_run_specs()
for rs in rspecs:
    src, srcty, dst, dstty = rs.args
    src, srcty, dst, dstty = src[0], srcty[0], dst[0], dstty[0]

    if srcty not in all_types:
        log.error("Conversion from %s not supported" % (srcty,))
        sys.exit(1)

    if dstty not in all_types:
        log.error("Conversion to %s not supported" % (dstty,))
        sys.exit(1)

    c = convgraph.get_conversion(src, srcty, dst, dstty, {})
    if not c:
        log.error("Conversion from %s to %s not supported" % (srcty, dstty))
        sys.exit(1)

    for cmd, fs, fsty, ds, dsty in c:
        assert cmd == "convert_direct", "Unsupported: %s" % (cmd,)
        assert (fsty, dsty) in conv, "Planner got it wrong: %s -> %s unsupported" % (fst, dsty)

        if os.path.exists(ds):
            continue

        cmd = cs.objects[conv[(fsty, dsty)]]['cmd']
        cmd = cmd.format(src = fs, dst=ds)

        targets.append(ds)
        out.append("""
{dst}: {src}
\t{cmd}""".format(src=fs, dst=ds, cmd=cmd))

if len(targets):
    print "all: %s" % (" ".join(targets))
    print "\n".join(out)

