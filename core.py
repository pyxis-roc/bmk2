import os
import subprocess
import tempfile
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
AT_TEMPORARY_INPUT = 5

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

    def __str__(self):
        return ", ".join(["%s=%s" % (x, getattr(self, x)) for x in vars(self)])

class Binary(object):
    def get_id(self):
        raise NotImplementedError

    def filter_inputs(self, inputs):
        raise NotImplementedError

class Input(object):
    def __init__(self, props, db = None):
        self.props = Properties()
        self.db = db

        for k, v in props.iteritems():
            setattr(self.props, k, v)

        self.name = self.props.name

    def get_alt_format(self, fmt):
        return self.db.get_alt_format(self.name, fmt)

    def hasprop(self, prop):
        return hasattr(self.props, prop)

    def get_id(self):
        return self.name

    def get_file(self):
        raise NotImplementedError

    def __str__(self):
        return "%s(%s)" % (self.name, str(self.props))

    __repr__ = __str__

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
        self.run_ok = False
        self.check_ok = False

    def run(self, inherit_tmpfiles = None):
        cmdline = [self.binary]

        for a, aty in self.args:
            if aty == AT_INPUT_FILE_IMPLICIT:
                continue

            if aty == AT_TEMPORARY_OUTPUT:
                th, self.tmpfiles[a] = tempfile.mkstemp(prefix="test-" + self.bin_id)
                os.close(th)
                log.debug("Created temporary file '%s' for '%s'" % (self.tmpfiles[a], a))
                a = self.tmpfiles[a]
            elif aty == AT_TEMPORARY_INPUT:
                a = inherit_tmpfiles[a]

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


class BasicRunSpec(object):
    def __init__(self):
        self.binary = None
        self.args = []
        self.env = {}
        self.runs = []
        self.in_path = False

    def get_id(self):
        return "%s/%s" % (self.bid, self.input_name)

    def set_binary(self, cwd, binary, in_path = False):
        self.cwd = cwd # TODO: does this do anything?
        self.binary = os.path.join(cwd, binary)
        self.in_path = in_path

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
        if not self.binary:
            log.error("No binary specified [bin %s]" % (self.bid,))
            return False

        # make sure binary exists
        if not self.in_path and not os.path.exists(self.binary):
            log.error("Binary %s not found [bin %s]" % (self.binary, self.bid))
            return False
            
        if not self.in_path and not os.path.isfile(self.binary):
            log.error("Binary %s is not a file [bin %s]" % (self.binary, self.bid))
            return False
            
        for a in self.get_input_files():
            if not os.path.exists(a):
                log.error("Input file '%s' does not exist [bin %s]" % (a, self.bid))
                return False

            # TODO: add AT_DIR ...
            if not os.path.isfile(a):
                log.error("Input file '%s' is not a file [bin %s]" % (a, self.bid))
                return False

        return True

    def run(self, **kwargs):
        x = Run(self.env, self.binary, self.args)
        x.run(**kwargs)
        self.runs.append(x)
        return x

    def __str__(self):
        ev = ["%s=%s" % (k, v) for k, v in self.env.iteritems()]
        args = ["%s" % (a) for a, b in self.args]
        return "%s %s %s" % (" ".join(ev), self.binary, " ".join(args))
        
class RunSpec(BasicRunSpec):
    def __init__(self, bmk_binary, bmk_input):
        super(RunSpec, self).__init__()

        self.bmk_binary = bmk_binary
        self.bmk_input = bmk_input
        
        self.bid = self.bmk_binary.get_id()
        self.input_name = bmk_input.get_id()
        self.checker = None
        self.perf = None

    def set_checker(self, checker):
        self.checker = checker

    def set_perf(self, perf):
        self.perf = perf

    def check(self):
        if not super(RunSpec, self).check():
            return False

        if not self.checker:
            log.error("No checker specified for input %s [bin %s] " % (self.input_name, self.bid))
            return False

        if not self.perf:
            log.error("No perf specified for input %s [bin %s] " % (self.input_name, self.bid))
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