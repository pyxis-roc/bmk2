import glob
import os
import logging
import ConfigParser

log = logging.getLogger(__name__)

FT_BISPEC = 1
FT_INPUTDB = 2
FT_INPUTPROPS = 3
FT_INPUTPROC = 4

FT_FIRST = FT_BISPEC
FT_LAST = FT_INPUTPROC

FT_MULTIPLE_OKAY = set()
FT_ZERO_OKAY = set([FT_INPUTPROPS, FT_INPUTPROC])
FT_GLOBS = {FT_BISPEC: '*.bispec', 
            FT_INPUTDB: '*.inputdb',
            FT_INPUTPROPS: '*.inputprops', 
            FT_INPUTPROC: None}

class Config(object):
    def __init__(self, metadir, inpproc = None):
        self.metadir = metadir
        self.okay = False
        self.files = {}
        self.disable_binaries = set()

        if inpproc is not None:
            self.files = {FT_INPUTPROC: inpproc}

    def set_file(self, f, ty, multiple = False):
        assert not (ty < FT_FIRST or ty > FT_LAST), "Invalid file type: %d" % (ty,)
        
        if multiple:
            assert ty in FT_MULTIPLE_OKAY, "File type %d not in multiple" % (ty,)

        if not (os.path.exists(f) and os.path.isfile(f)):
            log.error("File '%s' (file type: %d) does not exist or is not a file" % (f, ty))
            return False

        if ty not in self.files:
            if multiple:
                self.files[ty] = [f]
            else:
                self.files[ty] = f
        else:
            if multiple:
                self.files[ty].append(f)
            else:
                log.warning("Overwriting file type %d (currently: %s) with %s" % (ty, self.files[ty], f))
                self.files[ty] = f

        return True

    def get_file(self, ty):
        if ty not in self.files:
            return None

        return self.files[ty]
        
    def load_config(self):
        if not (os.path.exists(self.metadir) and os.path.isdir(self.metadir)):
            log.error("Metadir '%s' does not exist or is not a directory" % (self.metadir,))
            return False

        self.config_file = os.path.join(self.metadir, "bmk2.cfg")
        if not (os.path.exists(self.config_file) and os.path.isfile(self.config_file)):
            log.error("Configuration file '%s' does not exist" % (self.config_file,))
            return False
        
        x = ConfigParser.SafeConfigParser()
        with open(self.config_file, "rb") as f:
            x.readfp(f)

            try:
                version = x.get("bmk2", "version")
                if version != "2":
                    log.error("%s: Unknown config version %s" % (self.config_file, version,))
                    return False
            except ConfigParser.NoOptionError:
                log.error("%s: Unable to read version" % (self.config_file,))
                return False

            for prop, ty in [("inpproc", FT_INPUTPROC),
                             ("inputdb", FT_INPUTDB),
                             ("inputprops", FT_INPUTPROPS),
                             ("bispec", FT_BISPEC)]:
                try:
                    val = x.get("bmk2", prop)
                    val = os.path.join(self.metadir, val)
                    if self.set_file(val, ty):
                        log.info("%s: Loaded file type %d ('%s')" % (self.config_file, ty, val))
                    else:
                        return False
                except ConfigParser.NoOptionError:
                    log.debug("%s: File type %d (property: '%s') not specified" % (self.config_file, ty, prop))

            try:
                val = x.get("bmk2", "disable_binaries")
                self.disable_binaries = set([xx.strip() for xx in val.split(",")])
            except ConfigParser.NoOptionError:
                pass

            self.cfg = x
            return True
                    
    def get_var(self, key, default = None, sec = "bmk2"):
        try:
            return self.cfg.get(sec, key)
        except ConfigParser.NoOptionError:
            return default

    def auto_set_files(self):
        for ty in range(FT_FIRST, FT_LAST):
            if ty not in self.files and FT_GLOBS[ty] is not None:
                matches = glob.glob(os.path.join(self.metadir, FT_GLOBS[ty]))

                if len(matches) == 0:
                    if ty not in FT_ZERO_OKAY:
                        log.error("File type %d (%s) required, but not found in %s" % (ty, FT_GLOBS[ty], self.metadir))
                        return False
                elif len(matches) == 1:
                    log.info("File type %d auto set to %s" % (ty, matches[0]))
                    if not self.set_file(matches[0], ty, False):
                        return False
                elif len(matches) > 1:
                    if ty not in FT_MULTIPLE_OKAY:
                        log.error("Multiple matches found for file type %d (%s) in %s, must specify only one." % (ty, FT_GLOBS[ty], self.metadir))
                        return False
                    else:
                        for f in matches:
                            if not self.set_file(f, ty, True):
                                return False

        return True

__all__  = ['FT_BISPEC', 'FT_INPUTDB', 'FT_INPUTPROC', 'FT_INPUTPROPS',
            'Config']

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    inpproc = None

    if len(sys.argv) > 2:
        inpproc = sys.argv[2]

    x = Config(sys.argv[1], inpproc)
    if x.load_config():
        if x.auto_set_files():
            print "LOADED CONFIG"
