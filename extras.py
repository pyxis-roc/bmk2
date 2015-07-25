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

if __name__ == '__main__':
    import sys
    print scan(sys.argv[1], "bmktest2.py")
    

