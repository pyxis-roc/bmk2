#
# checkers.py
#
# Checkers available for tests in bmk2.
#
# Copyright (c) 2015, 2016 The University of Texas at Austin
#
# Author: Sreepathi Pai <sreepai@ices.utexas.edu>
#
# Intended to be licensed under GPL3

from core import Run, AT_OPAQUE
import re
import logging
import os
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

        if os.name != "nt":
        
            x = Run({}, "diff", [(x, AT_OPAQUE) for x in ["-q"] + args])
            if not x.run():
                log.info("diff -u '%s' '%s'" % tuple(args))
                return False

            run.check_ok = True   
        else:
            x = Run({}, "fc.exe", [(x, AT_OPAQUE) for x in args])
            if not x.run():
                log.info("fc.exe '%s' '%s'" % tuple(args))
                return False

            run.check_ok = True
        return True

class NumDiffChecker(Checker):
    def __init__(self, file1, gold, options=None):
        self.file1 = file1
        self.gold = gold
        self.options = [] if options is None else options
        
    def get_input_files(self):
        return [self.gold]

    def check(self, run):
        if not run.run_ok:
            log.error("Cannot check failed run %s" % (run))
            return False

        args = run.get_tmp_files([self.file1, self.gold])

        if os.name != "nt":
        
            x = Run({}, "numdiff", [(x, AT_OPAQUE) for x in (["-q"]  + self.options + args)])
            if not x.run():
                log.info("numdiff %s '%s' '%s'" % tuple([" ".join(self.options)] + args))
                return False

            run.check_ok = True   
        else:

            # Here we go through bash for windows because numdiff isn't on windows.

            # To get a properly cased filed path (required for bash)
            # to install for python2.7:
            # pip install pypiwin32
            import win32api
            args = [win32api.GetLongPathName(win32api.GetShortPathName(x)) for x in args]

            # Now replace drive to use bash on windows format. e.g. c: gets replaced to /mnt/c/
            # and \ gets replaced with /
            def windows_drive_to_bash(p):
                drive = p[0].lower()
                return "/mnt/" + drive + p[2:]
                
            args = [windows_drive_to_bash(x.replace("\\", "/")) for x in args]
            
            x = Run({}, "numdiff.bat", [(x, AT_OPAQUE) for x in (self.options + args)])
            if not x.run():
                log.info("numdiff.bat  %s '%s' '%s'" % tuple([" ".join(self.options)] + args))
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

        for o in [run.stdout, run.stderr]:
            #Tyler: have to remove the annoying windows \r character
            m = self.re.search(o.replace("\r","")) #TODO: stderr?
            if m:
                run.check_ok = True
                break
        else:
            log.info("REChecker could not match '%s'" % (self.re.pattern))

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
        
        x = self.rs.run(run.runid + ".external-checker", inherit_tmpfiles = run.tmpfiles)
        if not x.run_ok:
            return False

        run.check_ok = True
        return run.check_ok
    
