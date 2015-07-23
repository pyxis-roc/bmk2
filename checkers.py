from core import Run, AT_OPAQUE
import re
import logging
log = logging.getLogger(__name__)

class Checker(object):
    check_ok = False

    def check(self, run):
        pass

    def get_input_files(self):
        return []

class PassChecker(Checker):
    def check(self, run):
        run.check_ok = run.run_ok
        return run.run_ok

class DiffChecker(Checker):
    def __init__(self, file1, gold):
        self.file1 = file1
        self.gold = gold
        
    def get_input_files(self):
        return [self.gold]

    def check(self, run):        
        if not run.run_ok:
            log.error("Cannot check failed run %s" % (run))
            return False

        args = run.get_tmp_files([self.file1, self.gold])
        
        x = Run({}, "diff", [(x, AT_OPAQUE) for x in ["-q"] + args])
        if not x.run():
            log.info("diff -u '%s' '%s'" % tuple(args))
            return False

        run.check_ok = True
        return True

class REChecker(Checker):
    def __init__(self, rexp):
        self.re = re.compile(rexp, re.MULTILINE)
        
    def check(self, run):        
        if not run.run_ok:
            log.error("Cannot check failed run %s" % (run))
            return False

        m = self.re.search(run.stdout) #TODO: stderr?
        if m:
            run.check_ok = True

        return run.check_ok

class ExternalChecker(Checker):
    def __init__(self, brs):
        self.rs = brs

    def get_input_files(self):
        out = []
        if not self.rs.in_path:
            out.append(self.rs.binary)

        return out + self.rs.get_input_files()

    def check(self, run):
        if not run.run_ok:
            log.error("Cannot check failed run %s" % (run))
            return False
        
        x = self.rs.run(inherit_tmpfiles = run.tmpfiles)
        if not x.run_ok:
            return False

        run.check_ok = True
        return run.check_ok
    
