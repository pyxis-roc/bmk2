import sys
from common import *
from config import *
import glob
import os
import inputdb
import bispec
from core import *
from checkers import *
from perf import *

import logging
log = logging.getLogger(__name__)

def load_binary_specs(f):
    g = load_py_module(f)

    if 'BINARIES' in g:
        return g['BINARIES']
    else:
        log.error("No BINARIES in " + f)
        return None
       
class Loader(object):
    def __init__(self, metadir, inpproc):
        self.config = Config(metadir, inpproc)        
        self.binaries = {}
        self.bin_inputs = {}
        self.inp_filtered = False

    def initialize(self):
        if not self.config.load_config():
            return False
        
        if not self.config.auto_set_files():
            return False

        self.inputdb = inputdb.InputDB(self.config.get_file(FT_INPUTDB), 
                                       self.config.get_file(FT_INPUTPROC),
                                       self.config.get_file(FT_INPUTPROPS))
        self.inputdb.load()
        self.bs = bispec.read_bin_input_spec(self.config.get_file(FT_BISPEC))
        self.bs.set_input_db(self.inputdb)

        return True

    def split_binputs(self, binputs):
        bins = set()
        inputs = set()

        if binputs:
            inpnames = self.inputdb.inpnames

            for i in binputs:
                if i in inpnames:
                    inputs.add(i)
                else:
                    bins.add(i)

        self.inp_filtered = len(inputs) > 0

        return inputs, bins            

    def load_binaries(self, binspec, sel_binaries = None):
        d = os.path.dirname(binspec)
        binaries = load_binary_specs(binspec)
        if binaries:
            for b in binaries:
                if b.get_id() in self.binaries:
                    log.error("Duplicate binary id %s in %s" % (b.get_id(), binspec))
                    return False

                if sel_binaries and b.get_id() not in sel_binaries:
                    log.debug("Ignoring binary id %s in %s, not in sel_binaries" % (b.get_id(), binspec))
                    continue

                self.binaries[b.get_id()] = b
                b.props._cwd = d

            return True
        
        if not binaries or len(binaries) == 0:
            log.error("BINARIES is empty in " + binspec)

        return False

    def associate_inputs(self, binputs = None):
        if len(self.binaries) == 0:
            log.error("No binaries")
            return False

        for bid, b in self.binaries.iteritems():
            i = self.bs.get_inputs(b, binputs)
            if len(i) == 0:
                if not self.inp_filtered:
                    log.error("No inputs matched for binary " + bid)
                    return False
                else:
                    log.warning("No inputs matched for binary " + bid)
                    continue

            i = b.filter_inputs(i)
            if len(i) == 0:
                if not self.inp_filtered:
                    log.error("Filtering discarded all inputs for binary " + bid)
                    return False
                else:
                    log.warning("Filtering discarded all inputs for binary " + bid)
                    continue
            
            self.bin_inputs[bid] = i

        return True

    def get_run_specs(self):
        out = []
        for bid, b in self.binaries.iteritems():
            for inp in self.bin_inputs[bid]:
                out.append(b.get_run_spec(inp))

        return out

if __name__ == "__main__":
    import sys
    x = load_binary_specs(sys.argv[1])
    for bmk in x:
        print bmk.get_id()
        bmk.props.dump()
