import os
import fnmatch

def scan(path, glob):
    out = []
    for root, dirnames, filenames in os.walk(path):
        matches = fnmatch.filter(filenames, glob)
        out += [os.path.join(root, m) for m in matches]

    return out

def summarize(log, rspecs):
    bins = set([rs.bmk_binary.get_id() for rs in rspecs])
    inputs = set([rs.bmk_input.get_id() for rs in rspecs])

    runs = 0
    failed_runs = 0
    failed_checks = 0

    for rs in rspecs:
        runs += len(rs.runs)
        failed_runs += len(filter(lambda x: not x.run_ok, rs.runs))
        failed_checks += len(filter(lambda x: not x.check_ok, rs.runs))

    log.info('Summary: Runspecs: %s Binaries: %d Inputs: %d  Total runs: %d Failed: %d Failed Checks: %d' % (len(rspecs), len(bins), len(inputs), runs, failed_runs, failed_checks))

def standard_loader(metadir, inpproc, binspec, scandir, bispec, binputs = "", ignore_missing_binaries = False):
    import bmk2
    import config
    import sys

    if scandir:
        basepath = os.path.abspath(scandir)
        binspecs = scan(scandir, "bmktest2.py")
    else:
        if not os.path.exists(binspec):
            print >>sys.stderr, "Unable to find %s" % (binspec,)
            return False

        basepath = os.path.abspath(".")
        binspecs = [binspec]

    l = bmk2.Loader(metadir, inpproc)

    ftf = {}
    if bispec:
        f = None
        if os.path.exists(bispec) and os.path.isfile(bispec):
            f = bispec
        else:
            f = l.config.get_var("bispec_" + bispec, None)
            f = os.path.join(metadir, f)

        assert f is not None, "Unable to find file or spec in config file for bispec '%s'" % (bispec,)
        ftf[config.FT_BISPEC] = f

    if not l.initialize(ftf): return False
    sel_inputs, sel_binaries = l.split_binputs(binputs)

    sys.path.append(metadir)
    if not l.load_multiple_binaries(binspecs, sel_binaries) and not ignore_missing_binaries: return False
    if not l.associate_inputs(sel_inputs): return False

    return (basepath, binspecs, l)

if __name__ == '__main__':
    import sys
    print scan(sys.argv[1], "bmktest2.py")
    

