#
# core.py
#
# Core object classes and functions for bmk2.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

import os
import subprocess
import tempfile
import logging

if os.name != "nt":
    import resource

import re

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
AT_LOG = 6

placeholder_re = re.compile(r'(@[A-Za-z0-9_]+)') # may need delimiters?

USE_TIMEOUT = True # use the timeout overlay with rlimit.CPU on Unix-based systems

def escape_for_filename(n):
    return n.replace("/", "_").replace(".", "").replace("\\","_")
    
def create_log(ftemplate, run):
    v = {'runid': run.runid}
    if 'xtitle' in run.rspec.vars:
        v['xtitle'] = run.rspec.vars['xtitle']
    else:
        v['xtitle'] = ''

    if run.rspec: v['rsid'] = escape_for_filename(run.rspec.get_id())

    complete = os.path.join(os.path.dirname(run.binary), ftemplate.format(**v))
    return complete

def squash_output(buf, max_bytes = 1600):
    if len(buf) <= max_bytes:
        return buf
    
    header = buf[:max_bytes/2]
    tail = buf[-max_bytes/2:]

    pos = header.rfind("\n")
    if pos != -1:
        # can trim by a lot ...
        header = header[:pos]

    pos = tail.find("\n")
    if pos != -1:
        # can trim by a lot ...
        tail = tail[pos+1:]

    return header + "\n *** SQUASHED *** \n " + tail    
    
def strip_repeated_lines(buf, min_repeat = 2, msg = '<< previous line repeated {count} times >>\n'):
    import cStringIO
    
    x = cStringIO.StringIO(buf)
    y = cStringIO.StringIO()

    prev = None
    repeat_count = 0
    hold_buf = ""

    for l in x:
        if l == prev:
            repeat_count += 1
            if repeat_count <= min_repeat:
                hold_buf = hold_buf + l
        else:
            if hold_buf:
                if repeat_count > min_repeat:
                    y.write(msg.format(count = repeat_count))
                else:
                    y.write(hold_buf)

            repeat_count = 0
            hold_buf = ""
            y.write(l)
            
        prev = l
    
    if hold_buf:
        if repeat_count > min_repeat:
            y.write(msg.format(count = repeat_count))
        else:
            y.write(hold_buf)

        repeat_count = 0
        hold_buf = ""

    return y.getvalue()

def run_command_system(cmd):
    cmd.append(os.environ['BMK2_APP'])
    cmd.append(os.environ['BMK2_INPUT'])
    rv = os.system(" ".join(cmd) + "> NUL")
    if rv != 0:
        log.error("Execute (system) failed (%d): " % (rv,) + " ".join(cmd))

    return (rv, "", "")
    

def run_command(cmd, stdout = True, stderr = True, env = None, popen_args = {}):
    output = None
    error = None
    
    stdouth = subprocess.PIPE
    stderrh = subprocess.PIPE
	
    try:
        #Things seem to run more reliably on windows if we add this.
        if os.name == "nt":
            popen_args["shell"] = True
			
        proc = subprocess.Popen(cmd, stdout=stdouth, stderr=stderrh, env = env, **popen_args)
        output, error = proc.communicate()
		
        if proc.returncode != 0:
            log.error("Execute failed (%d): " % (proc.returncode,) + " ".join(cmd))
            rv = proc.returncode
        else:
            rv = 0
    except OSError as e:
        #print >>sys.stderr, "Execute failed: (%d: %s) "  % (e.errno, e.strerror) + " ".join(cmd)
        log.error("Execute failed (OSError %d '%s'): "  % (e.errno, e.strerror) + " ".join(cmd))
        output = e.strerror
        rv = e.errno

    return (rv, output, error)

def run_command_old(cmd, stdout = True, stderr = True, env = None, popen_args = {}):
    
    if stderr:
        stdout = True
        stderrh = subprocess.STDOUT
    else:
        stderrh = None 

    output = None
    error = None

    if stdout:
        try:
            output = subprocess.check_output(cmd, stderr=stderrh, env = env, **popen_args)
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

class RLimit(object):
    def __init__(self):
        self.limits = {}
        self.mt = 1 # stores multithreaded info, but RLIMIT_CPU must be set to limit*mt

    def setrlimit(self, lim, val):
        self.limits[lim] = val

    def set(self):
        for lim, val in self.limits.iteritems():
            resource.setrlimit(lim, val)
            
class Binary(object):
    def get_id(self):
        raise NotImplementedError

    def filter_inputs(self, inputs):
        raise NotImplementedError

    def apply_config(self, config):
        raise NotImplementedError

class Converter(Binary):
    def get_run_spec(self, bmkinput):
        x = BasicRunSpec()
        x.set_binary('', 'convert', in_path = True)
        x.set_arg(bmkinput.props.file, AT_INPUT_FILE)
        x.set_arg(bmkinput.props.format, AT_OPAQUE)

        x.bmk_input = bmkinput

        alt = bmkinput.get_alt_format(self.format)

        if alt:
            # we allow this since converter will remove this later ...
            x.set_arg(alt.props.file, AT_OUTPUT_FILE)
        else:
            x.set_arg("@output", AT_OUTPUT_FILE)

        x.set_arg(self.format, AT_OPAQUE)

        return x

class Input(object):
    def __init__(self, props, db = None):
        self.props = Properties()
        self.db = db

        for k, v in props.iteritems():
            setattr(self.props, k, v)

        self.name = self.props.name

    def get_alt_format(self, fmt):
        return self.db.get_alt_format(self.name, fmt)

    def get_all_alt(self):
        return self.db.get_all_alt(self.name)

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
    def __init__(self, env, binary, args, rspec = None):
        self.env = env
        self.binary = binary
        self.args = args
        self.cmd_line_c = "not-run-yet"
        self.bin_id = escape_for_filename(self.binary)
        self.rspec = rspec
        self.runid = None

        self.retval = -1
        self.stdout = ""
        self.stderr = ""

        self.tmpdir = None
        self.tmpfiles = {}
        self.run_ok = False
        self.check_ok = False
        self.overlays = []
        self.popen_args = {}

    def set_popen_args(self, kwd, val):
        self.popen_args[kwd] = val

    def set_overlays(self, overlays):
        self.overlays = overlays

    def set_tmpdir(self, tmpdir):
        self.tmpdir = tmpdir

    def run(self, inherit_tmpfiles = None):
        assert self.retval == -1, "Can't use the same Run object twice"

        cmdline = [self.binary]
        
        for a, aty in self.args:
            if aty == AT_INPUT_FILE_IMPLICIT:
                continue

            if aty == AT_TEMPORARY_OUTPUT:
                km = placeholder_re.search(a)
                assert km is not None
                k = km.group(1) # this should really be folded into the argtype itself...

                th, self.tmpfiles[k] = tempfile.mkstemp(prefix="test-" + self.bin_id, dir=self.tmpdir)
                os.close(th) # else files will continue to occupy space even after they are deleted
                log.debug("Created temporary file '%s' for '%s'" % (self.tmpfiles[k], k))
                a = a.replace(k, self.tmpfiles[k])
            elif aty == AT_TEMPORARY_INPUT:
                km = placeholder_re.search(a)
                assert km is not None
                k = km.group(1)
                a = a.replace(k, inherit_tmpfiles[k])

            cmdline.append(a)
            
        env = self.env
        for ov in self.overlays:
            env, cmdline = ov.overlay(self, env, cmdline, inherit_tmpfiles)

        self.env = env
        self.cmd_line = cmdline
        self.cmd_line_c = " ".join(self.cmd_line)        

        log.info("Running %s" % (str(self)))

        run_env = os.environ.copy() # do this at init time instead of runtime?
        run_env.update(self.env)

        # grabbing env from earlier command so that numdiff checker can use it next
        if 'BMK2_INPUTID' in self.env:
            os.environ['BMK2_INPUT'] = self.env['BMK2_INPUTID']
        if 'BMK2_BINID' in self.env:
            os.environ['BMK2_APP'] = self.env["BMK2_BINID"].replace('/', '-') # Don't like / in file names
        
        # Hack because popen doesn't like to call batch files which call windows bash
        if "numdiff.bat" in self.cmd_line:
            self.retval, self.stdout, self.stderr = run_command_system(self.cmd_line)
        else:
            self.retval, self.stdout, self.stderr = run_command(self.cmd_line, env=run_env, popen_args = self.popen_args)
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
        self.overlays = []
        self._runids = set()
        self.rlimit = None
        self.tmpdir = None
        self.vars = {}

        self.errors = set()

    def set_tmpdir(self, tmpdir):
        self.tmpdir = tmpdir

    def add_overlay(self, overlay):
        self.overlays.append(overlay)

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
            self.errors.add('missing-binary')
            return False
            
        if not self.in_path and not os.path.isfile(self.binary):
            log.error("Binary %s is not a file [bin %s]" % (self.binary, self.bid))
            return False
            
        for a in self.get_input_files():
            if not os.path.exists(a):
                log.error("Input file '%s' does not exist [bin %s]" % (a, self.bid))
                self.errors.add('missing-input')
                return False

            # TODO: add AT_DIR ...
            if not os.path.isfile(a):
                log.error("Input file '%s' is not a file [bin %s]" % (a, self.bid))
                return False

        return True

    def run(self, runid, **kwargs):
        assert runid not in self._runids, "Duplicate runid %s" % (runid,)

        assert len(self.errors) == 0

        x = Run(self.env, self.binary, self.args, self)
        if self.rlimit:            
            if os.name != "nt":
                x.set_popen_args('preexec_fn', self.rlimit.set)
            elif os.name == "nt":
                log.info("Warning: rlimit not supported on Windows OS")

        x.set_overlays(self.overlays)
        x.set_tmpdir(self.tmpdir)
        x.runid = runid
        self._runids.add(runid)
        x.run(**kwargs)
        self.runs.append(x)
        return x

    def set_rlimit(self, rlimit):
        self.rlimit = rlimit

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
                log.error("Checker input file '%s' does not exist [bin %s]" % (a, self.bid))
                return False

            # TODO: add AT_DIR ...
            if not os.path.isfile(a):
                log.error("Checker input file '%s' is not a file [bin %s]" % (a, self.bid))
                return False

        return True
