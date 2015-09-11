#!/usr/bin/env python

from pyhop import *

def gr_to_dimacs(state, src, dst):
    return "%s ->gr_to_dimacs %s" % (src, dst)

def dimacs_to_gr(state, src, dst):
    return "%s ->dimacs_to_gr %s" % (src, dst)

def dimacs_to_other(state, src, dst):
    return "%s ->dimacs_to_other %s" % (src, dst)

conversions = {('binary/gr', 'text/dimacs'): gr_to_dimacs,
               ('text/dimacs', 'binary/gr'): dimacs_to_gr,
               ('text/dimacs', 'other/format1'): dimacs_to_other,
               ('other/format1', 'other/format'): dimacs_to_other}

# graph file converter

# exists format/A
# [B does not exist, A exists] convert A to B [A exists, B exists]
# converter A/fmt1 to B/fmt2

def convert_direct(state, a, fmt_a, b, fmt_b):
    # we must have a direct converter
    if (fmt_a, fmt_b) not in conversions:
        print "no direct conversion"
        return False

    if state.files[fmt_a] != a and state.existing[fmt_a] != a:
        print "src does not exist"
        return False

    if state.files[fmt_b] == b:
        print "dst exists"
        return False
    
    state.files[fmt_b] = b
    return state

declare_operators(convert_direct)

def convert_from_existing(state, a, fmt_a, b, fmt_b):
    if (fmt_a, fmt_b) in conversions:        
        return [('convert_direct', a, fmt_a, b, fmt_b)]

    for f, e in state.existing.iteritems():
        if state.files[f] is None:
            return [('convert', e, f, b, fmt_b)]

    return False

def convert_via(state, a, fmt_a, b, fmt_b):
    if (fmt_a, fmt_b) in conversions:
        return False
    else:
        for s, d in conversions:
            if s == fmt_a and state.files[d] is None:
                via = "%s_%s" % (a, d)
                return [('convert', a, fmt_a, via, d),
                        ('convert', via, d, b, fmt_b)]
        
        return False

declare_methods('convert', convert_from_existing, convert_via)

start_file = 'a'
start_file_fmt = 'binary/gr'

s = State('initial')
s.existing = {}
s.files = {}

for f1, f2 in conversions.keys():
    s.files[f1] = None
    s.files[f2] = None

s.files[start_file_fmt] = start_file

s.existing[start_file_fmt] = start_file
s.existing['other/format1'] = 'c'

x = pyhop(s, [('convert', 'a', 'binary/gr', 'b', 'other/format')], verbose=2)

if not x:
    print "conversion is unsupported"

