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

p = argparse.ArgumentParser("Generate conversion makefile")
p.add_argument("output", nargs="?", default="/dev/stdout")
p.add_argument("-d", dest="metadir", metavar="PATH", help="Path to load configuration from", default=".")
p.add_argument("--iproc", dest="inpproc", metavar="FILE", help="Input processor")
p.add_argument("--bs", dest="binspec", metavar="FILE", help="Binary specification", default="./bmktest2.py")
p.add_argument("--bispec", dest="bispec", metavar="FILE_OR_MNEMONIC", help="Binary+Input specification")
p.add_argument("--scan", dest="scan", metavar="PATH", help="Recursively search PATH for bmktest2.py")
p.add_argument("-v", dest="verbose", type=int, help="Verbosity", default=0)

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

    exists = {}
    for alt in rs.bmk_input.get_all_alt():
        if alt.props.format not in all_types:
            log.error("Format '%s' not listed in convspec"%  (alt.props.format,))
            sys.exit(1)

        if os.path.exists(alt.props.file):
            # sometimes alt.props.file may only exist in the database
            exists[alt.props.format] = alt.props.file

    # might be useful for a copy?
    if dstty in exists:
        del exists[dstty]

    #print exists

    if srcty not in all_types:
        log.error("Conversion from %s not supported" % (srcty,))
        sys.exit(1)

    if dstty not in all_types:
        log.error("Conversion to %s not supported" % (dstty,))
        sys.exit(1)

    if dst == "@output":
        dst = None

    # silently skip destinations that already exist in database and on disk
    if dst and os.path.exists(dst):
        # we're also abandoning any intermediate files ...
        # TODO: the planner should do this...
        continue

    c = convgraph.get_conversion(src, srcty, dst, dstty, exists, args.verbose)
    if not c:
        log.error("Conversion from %s to %s not supported" % (srcty, dstty))
        sys.exit(1)

    if False:
        print >>sys.stderr, c

    if dst is None:
        dst = c[-1][3]

    # skip destinations that only exist on disk but not in database
    if os.path.exists(dst):
        log.info("Destination `%s' already exists, you need to update inputdb." % (dst,))
        continue

    for cmd, fs, fsty, ds, dsty in c:
        assert cmd == "convert_direct", "Unsupported: %s" % (cmd,)
        assert (fsty, dsty) in conv, "Planner got it wrong: %s -> %s unsupported" % (fst, dsty)
        #print c

        if os.path.exists(ds):
            continue

        cmd = cs.objects[conv[(fsty, dsty)]]['cmd']
        cmd = cmd.format(src = fs, dst=ds, verbose=1)

        out.append("""
{dst}: {src}
\t{cmd}""".format(src=fs, dst=ds, cmd=cmd))

    targets.append(dst) # dst

if len(targets):
    f = open(args.output, "w")
    print >>f, "all: %s" % (" ".join(targets))
    print >>f, "\n".join(out)
    f.close()
