import sys
from common import *
import glob
import os
import inputdb
import bispec

class Properties(object):
    def dump(self):
        for y in vars(self):
            print y, getattr(self, y)

class Binary(object):
    def get_id(self):
        raise NotImplementedError

    def filter_inputs(self, inputs):
        raise NotImplementedError

class Input(object):
    def get_id(self):
        raise NotImplementedError

    def get_file(self):
        raise NotImplementedError

class Run(object):
    pass

AT_OPAQUE = 0
AT_INPUT_FILE = 1
AT_OUTPUT_FILE = 2
AT_TEMPORARY_OUTPUT = 3
AT_INPUT_FILE_IMPLICIT = 4

class RunSpec(object):
    def __init__(self):
        self.binary = None
        self.args = []
        self.env = {}

    def set_binary(self, cwd, binary, bid):
        self.cwd = cwd
        self.binary = os.path.join(cwd, binary)
        self.bid = bid

    def has_env_var(self, var):
        return var in self.env

    def set_env_var(self, var, value, replace = True):
        if var in self.env and not replace:
            raise IndexError

        self.env[var] = value

    def set_arg(self, arg, arg_type = AT_OPAQUE):
        self.args.append((arg, arg_type))

    def check(self):
        # make sure binary exists
        if not os.path.exists(self.binary):
            # must provide full-path even if in PATH ...
            print >>sys.stderr, "Binary %s not found [bin %s]" % (self.binary, self.bid)
            return False
            
        if not os.path.isfile(self.binary):
            print >>sys.stderr, "Binary %s is not a file [bin %s]" % (self.binary, self.bid)
            return False
            
        for a, aty in self.args:
            if aty in (AT_INPUT_FILE, AT_INPUT_FILE_IMPLICIT):
                if not os.path.exists(a):
                    print >>sys.stderr, "Input file %s does not exist [bin %s]" % (a, self.bid)
                    return False

                # TODO: add AT_DIR ...
                if not os.path.isfile(a):
                    print >>sys.stderr, "Input file %s is not a file [bin %s]" % (a, self.bid)
                    return False

        return True

    def __str__(self):
        ev = ["%s=%s" % (k, v) for k, v in self.env.iteritems()]
        args = ["%s" % (a) for a, b in self.args]
        return "%s %s %s" % (" ".join(ev), self.binary, " ".join(args))


def find_helper_files(d):
    specfiles = glob.glob(os.path.join(d, "*.bispec"))
    dbfiles = glob.glob(os.path.join(d, "*.inputdb"))

    if len(specfiles) != 1:
        return None

    if len(dbfiles) != 1:
        return None

    return specfiles[0], dbfiles[0]

def load_binary_specs(f):
    g = load_py_module(f)

    if 'BINARIES' in g:
        return g['BINARIES']
    else:
        print >>sys.stderr, "No BINARIES in ", f
        
class Loader(object):
    def __init__(self, metadir, inpproc):
        self.metadir = metadir
        self.inpproc = inpproc
        self.binaries = {}
        self.bin_inputs = {}

    def initialize(self):
        x =  find_helper_files(self.metadir)
        if not x:
            print >>sys.stderr, "Unable to find spec files (*.bispec) or inputdb files (*.inputdb) [or multiple exist] in", self.metadir
            return False

        self.inputdb = inputdb.read_cfg_file(x[1], self.inpproc)
        self.bs = bispec.read_bin_input_spec(x[0])
        self.bs.set_input_db(self.inputdb)

        return True

    def load_binaries(self, binspec):
        d = os.path.dirname(binspec)
        binaries = load_binary_specs(binspec)
        if binaries:
            for b in binaries:
                if b.get_id() in self.binaries:
                    print >>sys.stderr, "DUPLICATE %s binary in %s" % (b.get_id(), f)
                    return False

                self.binaries[b.get_id()] = b
                b.props._cwd = d

            return True
        
        if len(binaries) == 0:
            print >>sys.stderr, "BINARIES is empty in ", f

        return False

    def associate_inputs(self):
        for bid, b in self.binaries.iteritems():
            i = self.bs.get_inputs(b)
            if len(i) == 0:
                print >>sys.stderr, "No inputs matched for binary", bid
                return False

            i = b.filter_inputs(i)
            if len(i) == 0:
                print >>sys.stderr, "Filtering discarded all inputs for binary", bid
                return False
            
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


