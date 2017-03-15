#!/usr/bin/env python

# index, css, html, diffs

import logproc
import argparse
import re
from collections import namedtuple
import subprocess
import os

output_prefix = namedtuple('output_prefix', ['type', 'binid', 'output_type', 'raw'])

info_out_re = re.compile("^INFO ([^ :]+) (STDOUT|STDERR)$")
info_running_re = re.compile("^INFO Running (.+)$")
info_cfg_re = re.compile("^INFO Applying configuration (.+)$")
info_diff_re = re.compile("^INFO (diff -u.*)$")

repeat_line_re  = 	re.compile("<< previous line repeated [0-9]+ times >>")
squashed_line_re = re.compile(r" \*\*\* SQUASHED \*\*\* ")

def get_diff_output(cmdline, run):
    fn = "diff_%s_%d.txt" % (run.start_date.replace(" ", "_").replace(":", "_"), run.run)

    f = open(fn, "w")
    subprocess.call(cmdline, stdout= f ,stderr=subprocess.STDOUT, shell=True)
    f.close()

    st = os.stat(fn)
    SZ = 1048576
    if st.st_size > SZ:
        fn2 = fn[:-4] + ".html"

        f = open(fn, "r")
        content = f.readlines(SZ)
        f.close()

        f = open(fn2, "w")
        print >>f, """<!DOCTYPE html><html><body>
        <p>This is only the first few megabytes of the <a href='{fulldiff}'>actual full diff</a> ({size} MB).</p>
        <pre>{content}</pre></body></html>""".format(fulldiff=fn, size = st.st_size / 1048576, content = "".join(content))
        f.close()
        fn = fn2

        
    return fn 

class Handler(object):
    def start_date(self, r):
        pass

    def end_date(self, r):
        pass

    def run_begin(self, r):
        pass

    def run_end(self, r):
        pass

    def perf(self, r):
        pass

    def missing(self, r):
        pass

    def collect(self, r):
        pass

    def instr(self, r):
        pass

    def task_complete(self, r):
        pass

    def fail(self, r):
        pass

    def pass_(self, r):
        pass

    def generic_log(self, r):
        pass

    def unmatched(self, r):
        pass

class Run(object):
    run = None
    idxid = None
    
    components = None
    name = None
    runid = None
    status = None
    time_ns = None

    def __init__(self, run):
        self.run = run
        self.perf_runid = None
        self.components = []

    def set_name(self, name):
        assert self.name is None, "%s %s" % (self.name, name)
        self.name = name

    def set_runid(self, runid):
        assert self.runid is None, "%s %s" % (self.runid, runid)
        self.runid = runid

    def set_status(self, status):
        assert self.status is None, "%s %s" % (self.status, status)
        self.status = status

    def set_perf(self, time_ns):
        assert self.time_ns is None, "%s %s" % (self.time_ns, time_ns)
        self.time_ns = time_ns



class HTMLize(Handler):
    in_output = False
    run = 0
    runs = None

    def __init__(self, f, diffs = True):
        self.f = f
        self.runs = []
        self.diffs = diffs
        self.lineno = 0

    def begin(self, logfile):
        self.lineno = 0
        print >>self.f, """<!DOCTYPE html>
<html>
<title>{logfile}</title>
<link rel='stylesheet' type='text/css' href='summ.css' />
<body>
<h1>{logfile}</h1>
<div id='container'>

<div id='logcontents'>
<h2>Log file contents</h2>
<pre id='log'>""".format(logfile=logfile)

    def write_idx(self):
        print >>self.f, "<div id='index'><h2>Index</h2>"
        st = {'PASS': 'pass', 'FAIL/CHECK': 'failcheck', 'FAIL/RUN': 'failrun'}

        print >>self.f, "<p>There are a total of %d runs in this log.</p>" % (len(self.runs))

        lastname = None
        for i, r in enumerate(self.runs):            
            print r.name, lastname
            if r.name != lastname:
                if lastname is not None: 
                    print >>self.f, "</ul>"
                    print >>self.f, "</div>"

                lastname = r.name
                print >>self.f, "<div id='idx-%s'>" % (r.name,)
                print >>self.f, "<h3>", r.name, "</h3>"
                print >>self.f, "<ul>"

            print >>self.f, "<li><a href='#{idxid}'>Run {run}</a>".format(idxid=r.idxid, run=r.run)

            print >>self.f, " <span class='st_{cst}'>{st}</span>".format(cst=st[r.status], st=r.status)
            
            if r.time_ns is not None:
                print >>self.f, " (%0.2f ms)" % (float(r.time_ns) / 1E6,)

            for d, l in r.components:
                print >>self.f, " <a href='#{id_}'>[{desc}]</a>".format(desc=d, id_=l)

            print >>self.f, "</li>"

        print >>self.f, "</ul>"
        print >>self.f, "</div>"
        print >>self.f, "</div>"


    def end(self):
        self.f.write("\n</pre></div>\n")
        self.write_idx()
        self.f.write("</div></body></html>\n")

    def write_ll(self, logline, number = True):
        if number:
            self.lineno += 1
            self.f.write("<span class='lineno' id='line%d'>%d</span>" % (self.lineno, self.lineno) + logline)
        else:
            self.f.write(logline)
        
    def start_date(self, r):
        self.start_date = r.start_date
        self.write_ll(r.raw)

    def end_date(self, r):
        self.write_ll(r.raw)

    def run_begin(self, r):
        #print r.raw

        rr = Run(self.run)
        rr.start_date = self.start_date
        rr.idxid = "perf_begin_run:{run}".format(run = self.run)
        x = "<span class='perf_run_begin' id='{id_}'>{raw}</span>".format(id_=rr.idxid, raw=r.raw)
        self.runs.append(rr)
        self.write_ll(x)
        self.run += 1       


    def run_end(self, r):
        #print r.raw
        self.write_ll(r.raw)

    def perf(self, r):
        rr = self.runs[-1]
        rr.set_perf(r.time_ns)
        self.write_ll(r.raw)

    def missing(self, r):
        self.write_ll(r.raw)

    def collect(self, r):
        self.write_ll(r.raw)

    def instr(self, r):
        self.write_ll(r.raw)

    def task_complete(self, r):
        self.write_ll(r.raw)

    def fail(self, r):
        #print r.raw
        failcls = "fail"

        if "re-running" not in r.message:
            rr = self.runs[-1]

            rr.set_name(r.binid)
            rr.set_runid(r.runid)

            if "run failed" in r.message:
                rr.set_status("FAIL/RUN")
            elif "check failed" in r.message:
                rr.set_status("FAIL/CHECK")
            else:
                rr.set_status("FAIL/?")
        else:
            failcls = "fail_rerun"

        self.write_ll("<span class='%s'>" % (failcls,) + r.raw + "</span>")


    def pass_(self, r):
        #print r.raw

        rr = self.runs[-1]
        
        rr.set_name(r.binid)
        rr.set_status("PASS")

        self.write_ll("<span class='pass'>" + r.raw + "</span>")


    def output_prefix(self, r):
        self.in_output = True
        rr = self.runs[-1]

        id_ = "info_%s_%d" % (r.output_type, rr.run)
        rr.components.append((r.output_type, id_))
        self.write_ll("<span id='{id_}' class='op_{class_}'>{raw}</span>".format(id_=id_, raw=r.raw, class_=r.output_type.lower()))

    def generic_log(self, r):
        if r.loglevel == "INFO":
            m = info_out_re.match(r.raw)
            if m:
                binid = m.group(1)
                otype = m.group(2)
                
                r = output_prefix('OUTPUT_PREFIX', binid=binid, output_type = otype, raw = r.raw)
                self.output_prefix(r)
                return

            m = info_running_re.match(r.raw)
            if m:
                cmdline = m.group(1)
                rr = self.runs[-1]

                if "BMK2_RUNID" in cmdline:
                    self.write_ll("INFO Running <span class='cmdline' id='cmdline_%d'>" % (rr.run,) + cmdline + "</span>\n")
                    rr.components.append(('CMDLINE', 'cmdline_%d' % (rr.run,)))
                else:
                    self.write_ll("INFO Running <span class='cmdline'>" + cmdline + "</span>\n")

                return

            m = info_cfg_re.match(r.raw)
            if m:
                cfg = m.group(1)
                self.write_ll(r.raw)
                return

            m = info_diff_re.match(r.raw)
            if m:
                cmdline = m.group(1)

                if self.diffs:
                    fname = get_diff_output(cmdline, self.runs[-1])
                    rr = self.runs[-1]

                    diff_id = "diff_%d" % (rr.run,)

                    rr.components.append(('DIFF', diff_id))

                    self.write_ll("INFO <a href='%s' id='%s'>" % (fname, diff_id) + cmdline + "</a>\n")
                else:
                    self.write_ll(r.raw)

                return

        elif r.loglevel == "ERROR":
            self.write_ll(r.raw[:-1])

            if "Execute failed" in r.raw and "(1): diff" not in r.raw:
                self.write_ll(" <a href='#info_STDERR_%d'>[STDERR]</a>" % (self.runs[-1].run,), number=False)

            self.write_ll("\n", number=False)
                
            return

        self.in_output = False
        self.write_ll(r.raw)

    def unmatched(self, r):
        if self.in_output:
            if repeat_line_re.match(r.raw) is not None:
                self.write_ll("\t<span class='repeat_line'>" + r.raw + "</span>")
            elif squashed_line_re.match(r.raw) is not None:
                self.write_ll("\t<span class='squash_line'>" + r.raw + "</span>")
            else:
                self.write_ll("\t<span class='output'>" + r.raw + "</span>")
        else:
            self.write_ll(r.raw)

def process_log_file(logfile, handler):
    handler.begin(logfile)

    for r in logproc.parse_log_file(logfile, extended = True):
        if r.type == "START_DATE":
            handler.start_date(r)
        elif r.type == "END_DATE":
            handler.end_date(r)
        elif r.type == "RUN_BEGIN":
            handler.run_begin(r)
        elif r.type == "RUN_END":
            handler.run_end(r)
        elif r.type == "PERF":
            handler.perf(r)
        elif r.type == "MISSING":
            handler.missing(r)
        elif r.type == "COLLECT":
            handler.collect(r)
        elif r.type == "INSTR":
            handler.instr(r)
        elif r.type == "TASK_COMPLETE":            
            handler.task_complete(r)
        elif r.type == "FAIL":
            handler.fail(r)
        elif r.type == "PASS":
            handler.pass_(r)            
        elif r.type == "UNMATCHED":
            handler.unmatched(r)
        elif r.type == "GENERIC_LOG":
            handler.generic_log(r)
        else:
            assert False, r.type

    handler.end()


parser = argparse.ArgumentParser(description="Summarize a bmk2 log")

parser.add_argument("logfile", help="Log file")
parser.add_argument("output", help="Output file")
parser.add_argument("--no-diffs", help="Do not generate diff files", action="store_true")

args = parser.parse_args()

process_log_file(args.logfile, HTMLize(open(args.output, "w"), diffs=not args.no_diffs))
