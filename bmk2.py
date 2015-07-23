import sys
from common import *
from config import *
import glob
import os
import inputdb
import bispec
import subprocess
import tempfile
import inputprops
import logging

log = logging.getLogger(__name__)

if not hasattr(subprocess, "check_output"):
    print >>sys.stderr, "%s: Need python 2.7" % (sys.argv[0],)
    sys.exit(1)

AT_OPAQUE = 0
AT_INPUT_FILE = 1
AT_OUTPUT_FILE = 2
AT_TEMPORARY_OUTPUT = 3
AT_INPUT_FILE_IMPLICIT = 4

def run_command(cmd, stdout = True, stderr = True, env = None):
    if stderr:
        stdout = True
        stderrh = subprocess.STDOUT
    else:
        stderrh = None

    output = None
    error = None

    if stdout:
        try:
            output = subprocess.check_output(cmd, stderr=stderrh, env = env)
            rv = 0
        except subprocess.CalledProcessError as e:
            #print >>sys.stderr, "Execute failed (%d): " % (e.returncode,) + " ".join(cmd)
            log.error("Execute failed (%d): " % (e.returncode,) + " ".join(cmd))
            output = e.output
            rv = e.returncode
        except OSError as e:
            #print >>sys.stderr, "Execute failed: (%d: %s) "  % (e.errno, e.strerror) + " ".join(cmd)
            log.error("Execute failed (OSError %d '%s'): "  % (e.errno, e.strerror) + " ".join(cmd))
            output = e.strerror
            rv = e.errno
    else:
        rv = subprocess.call(cmd, stderr=stderrh)

    return (rv, output, error)

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
    def __init__(self, props):
        self.props = Properties()

        for k, v in props.iteritems():
            setattr(self.props, k, v)

        self.name = self.props.name

    def hasprop(self, prop):
        return hasattr(self.props, prop)

    def get_id(self):
        return self.name

    def get_file(self):
        raise NotImplementedError


class Run(object):
    def __init__(self, env, binary, args):
        self.env = env
        self.binary = binary
        self.args = args
        self.run_env = os.environ.copy()
        self.run_env.update(self.env)
        self.cmd_line_c = "not-run-yet"
        self.bin_id = self.binary.replace("/", "_").replace(".", "")

        self.retval = -1
        self.stdout = ""
        self.stderr = ""

        self.tmpfiles = {}


    def run(self):
        cmdline = [self.binary]

        for a, aty in self.args:
            if aty == AT_INPUT_FILE_IMPLICIT:
                continue

            if aty == AT_TEMPORARY_OUTPUT:
                th, self.tmpfiles[a] = tempfile.mkstemp(prefix="test-" + self.bin_id)
                log.debug("Created temporary file '%s' for '%s'" % (self.tmpfiles[a], a))
                a = self.tmpfiles[a]



            cmdline.append(a)
            
        self.cmd_line = cmdline
        self.cmd_line_c = " ".join(self.cmd_line)

        log.info("Running %s" % (str(self)))

        self.retval, self.stdout, self.stderr = run_command(self.cmd_line, env=self.run_env)
        self.run_ok = self.retval == 0

        return self.run_ok

    def get_tmp_files(self, names):
        out = []
        for n in names:
            if n[0] == "@":
                out.append(self.tmpfiles[n])
            else:
                out.append(n)

        return out

    def cleanup(self):
        for a, f in self.tmpfiles.iteritems():
            os.unlink(f)

    def __str__(self):
        ev = ["%s=%s" % (k, v) for k, v in self.env.iteritems()]
        return "%s %s" % (" ".join(ev), self.cmd_line_c)


class RunSpec(object):
    def __init__(self, bmk_binary, bmk_input):
        self.bmk_binary = bmk_binary
        self.bmk_input = bmk_input

        self.bid = self.bmk_binary.get_id()
        self.input_name = bmk_input.get_id()

        self.binary = None
        self.args = []
        self.env = {}
        self.runs = []
        self.checker = None
    
    def get_id(self):
        return "%s/%s" % (self.bid, self.input_name)

    def set_binary(self, cwd, binary):
        self.cwd = cwd
        self.binary = os.path.join(cwd, binary)
        self.bid = self.bmk_binary.get_id()

    def set_checker(self, checker):
        self.checker = checker

    def has_env_var(self, var):
        return var in self.env

    def set_env_var(self, var, value, replace = True):
        if var in self.env and not replace:
            raise IndexError

        self.env[var] = value

    def set_arg(self, arg, arg_type = AT_OPAQUE):
        self.args.append((arg, arg_type))

    def get_input_files(self):
        out = []
        for a, aty in self.args:
            if aty in (AT_INPUT_FILE, AT_INPUT_FILE_IMPLICIT):
                out.append(a)

        return out

    def check(self):
        # make sure binary exists
        if not os.path.exists(self.binary):
            # must provide full-path even if in PATH ...
            log.error("Binary %s not found [bin %s]" % (self.binary, self.bid))
            return False
            
        if not os.path.isfile(self.binary):
            log.error("Binary %s is not a file [bin %s]" % (self.binary, self.bid))
            return False
            
        if not self.checker:
            log.error("No checker specified for input  %s [bin %s] " % (self.input_name, self.bid))
            return False

        for a in self.get_input_files():
            if not os.path.exists(a):
                log.error("Input file '%s' does not exist [bin %s]" % (a, self.bid))
                return False

            # TODO: add AT_DIR ...
            if not os.path.isfile(a):
                log.error("Input file '%s' is not a file [bin %s]" % (a, self.bid))
                return False

        for a in self.checker.get_input_files():
            if not os.path.exists(a):
                log.error("Input file '%s' for checker does not exist [bin %s]" % (a, self.bid))
                return False

            # TODO: add AT_DIR ...
            if not os.path.isfile(a):
                log.error("Input file '%s' for checker is not a file [bin %s]" % (a, self.bid))
                return False

        return True

    def run(self):
        x = Run(self.env, self.binary, self.args)
        x.run()
        self.runs.append(x)
        return x

    def __str__(self):
        ev = ["%s=%s" % (k, v) for k, v in self.env.iteritems()]
        args = ["%s" % (a) for a, b in self.args]
        return "%s %s %s" % (" ".join(ev), self.binary, " ".join(args))


class Checker(object):
    def check(self, run):
        pass

    def get_input_files(self):
        return []

class PassChecker(Checker):
    def check(self, run):
        return run.run_ok

class DiffChecker(Checker):
    def __init__(self, file1, gold):
        self.file1 = file1
        self.gold = gold

    def get_input_files(self):
        return [self.gold]

    def check(self, run):
        if not run.run_ok:
            log.error("Cannot check failed run")
            return False

        args = run.get_tmp_files([self.file1, self.gold])
        
        x = Run({}, "diff", [(x, AT_OPAQUE) for x in ["-q"] + args])
        if not x.run():
            log.info("diff -u '%s' '%s'" % tuple(args))
            return False

        return True


def load_binary_specs(f):
    g = load_py_module(f)

    if 'BINARIES' in g:
        return g['BINARIES']
    else:
        logging.error("No BINARIES in " + f)
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

        bt = {}
        self.inputdb = inputdb.read_cfg_file(self.config.get_file(FT_INPUTDB), self.config.get_file(FT_INPUTPROC), bt)

        if self.config.get_file(FT_INPUTPROPS) is not None:
            self.inputprops = inputprops.read_prop_file(self.config.get_file(FT_INPUTPROPS), bt)
            inputprops.apply_props(self.inputdb, self.inputprops)
        else:
            self.inputprops = None

        self.inputdb = [Input(i) for i in self.inputdb]
        self.bs = bispec.read_bin_input_spec(self.config.get_file(FT_BISPEC))
        self.bs.set_input_db(self.inputdb)

        return True

    def split_binputs(self, binputs):
        inpnames = set([i.get_id() for i in self.inputdb])

        bins = set()
        inputs = set()

        if binputs:
            for i in binputs:
                if i in inpnames:
                    inputs.add(i)
                else:
                    bins.add(i)

        self.inp_filtered = len(inputs) > 0
        return inputs, bins            

    def load_binaries(self, binspec, binputs = None):
        d = os.path.dirname(binspec)
        binaries = load_binary_specs(binspec)
        if binaries:
            for b in binaries:
                if b.get_id() in self.binaries:
                    log.error("Duplicate binary id %s in %s" % (b.get_id(), binspec))
                    return False

                if binputs and b.get_id() not in binputs:
                    log.debug("Ignoring binary id %s in %s, not in sel_inputs" % (b.get_id(), binspec))
                    continue

                self.binaries[b.get_id()] = b
                b.props._cwd = d

            return True
        
        if len(binaries) == 0:
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
