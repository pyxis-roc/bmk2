#!/usr/bin/env python

import sys
import re
import logging

log = logging.getLogger(__name__)

class BinInputSpecV1(object):
    def __init__(self):
        self.rules = []
        self.inputs = {}

    def set_input_db(self, inputs):
        for i in inputs:
            nm = i.get_id()
            if nm not in self.inputs:
                self.inputs[nm] = {}

            self.inputs[nm][i.props.file] = i

    def get_inputs(self, binary, sel_inputs = None):
        inpnames = set()
        binid = binary.get_id()
        
        for (re, inp) in self.rules:
            if re.match(binid): # always anchored?
                inpnames = inpnames.union(inp)

        out = []
        for n in inpnames:
            if sel_inputs and n not in sel_inputs:
                log.debug("Ignoring input '%s' for '%s', not in sel_inputs" % (n, binid))
                continue

            assert n in self.inputs, "Input named %s not found" % (n,)
            out += self.inputs[n].values()

        return out

    def read(self, ff):
        out = []
        for l in ff:
            l = l.strip()
            if l[0] == "#":
                continue

            ls = l.split(" ", 1)
            binmatch = ls[0]
            inpnames = [x.strip() for x in ls[1].split(",")]
            out.append((re.compile(binmatch), set(inpnames)))
            
        self.rules = out

def read_bin_input_spec(f):
    with open(f, "rb") as ff:
        l = ff.readline().strip()
        if l == "#v1":
            x = BinInputSpecV1()
        else:
            printf >>sys.stderr, "Unknown file version for input/binary spec", l
    
        x.read(ff)

    return x

if __name__ == "__main__":
    read_bin_input_spec(sys.argv[1])
