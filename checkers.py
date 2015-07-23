from core import Run, AT_OPAQUE
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
            log.error("Cannot check failed run")
            return False

        args = run.get_tmp_files([self.file1, self.gold])
        
        x = Run({}, "diff", [(x, AT_OPAQUE) for x in ["-q"] + args])
        if not x.run():
            log.info("diff -u '%s' '%s'" % tuple(args))
            return False

        run.check_ok = True
        return True
