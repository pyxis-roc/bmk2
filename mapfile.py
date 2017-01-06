from collections import namedtuple
import re

run_re = re.compile(r"^([0-9]+\.[0-9]+\.[0-9]+)\.([0-9]+)$")

mapfile_entry = namedtuple('mapfile_entry', ['binid', 'input', 'runid', 'filetype', 'filename', 'abspath'])

def split_bininpid(bininpid):
    p = bininpid.rfind("/")
    return bininpid[:p], bininpid[p+1:]

def split_runid(runid):
    m = run_re.match(runid)

    if m:
        return m.group(1), m.group(2)
    else:
        return runid, None

def get_run(runid):
    m = run_re.match(runid)
    if m:
        return int(m.group(2))
    else:
        return None

def read_mapfile(mapfile):
    with open(mapfile, "r") as f:
        for l in f:
            # binid/input runid filetype filename abspath
            ls = l.strip().split(" ", 4)
            binid, input = split_bininpid(ls[0])

            if len(ls) != 5:
                print "ERROR: malformed mapfile entry", ls

            yield mapfile_entry(binid = binid, input = input, runid=ls[1], filetype=ls[2], filename=ls[3], abspath=ls[4])

def write_mapfile(mapfile, mapentries, mode="w"):
    f = open(mapfile, mode)
    
    for me in mapentries:
        assert me.input != ""
        
        print >>f, "%s/%s %s %s %s %s" % (me.binid, me.input, me.runid, me.filetype, me.filename, me.abspath)

    f.close()
        
def write_mapfile_raw(mapfile, mapentries, mode="w"):
    """For use by non-binary/input aware tools, input must be empty and binid contains the whole ID"""

    f = open(mapfile, mode)
    
    for me in mapentries:
        assert me.input == ""
        
        print >>f, "%s %s %s %s %s" % (me.binid, me.runid, me.filetype, me.filename, me.abspath)

    f.close()
        
