import core
import logging

log = logging.getLogger(__name__)

class Overlay(object):
    def __init__(self, env = {}, binary = None, args = []):
        self.env = env
        self.binary = binary
        self.args = args
        self.tmpfiles = {}

    def overlay(self, run, env, cmdline, inherit_tmpfiles = None):
        if env is None:
            new_env = None
        else:
            new_env = env.copy()
            new_env.update(self.env)

        new_cmdline = []
        if self.binary:
            new_cmdline.append(self.binary)

        for a, aty in self.args:
            if aty == AT_INPUT_FILE_IMPLICIT:
                continue

            if aty == AT_TEMPORARY_OUTPUT:
                th, self.tmpfiles[a] = tempfile.mkstemp(prefix="test-ov-")
                os.close(th)
                log.debug("Created temporary file '%s' for overlay parameter '%s'" % (self.tmpfiles[a], a))
                a = self.tmpfiles[a]
            elif aty == AT_TEMPORARY_INPUT:
                a = inherit_tmpfiles[a]

            new_cmdline.append(a)

        new_cmdline += cmdline

        return new_env, new_cmdline

    def cleanup(self):
        for a, f in self.tmpfiles.iteritems():
            os.unlink(f)

    def __str__(self):
        ev = ["%s=%s" % (k, v) for k, v in self.env.iteritems()]
        return "%s %s" % (" ".join(ev), self.cmd_line_c)

class CUDAProfilerOverlay(Overlay):
    def __init__(self, profile_cfg = None, profile_log = None):
        env = {'CUDA_PROFILE': '1'}
        if profile_cfg: env['CUDA_PROFILE_CONFIG'] = profile_cfg
        if profile_log: env['CUDA_PROFILE_LOG'] = profile_log

        self.profile_log = profile_log
        self.collect = logging.getLevelName('COLLECT')
        super(CUDAProfilerOverlay, self).__init__(env)

    def overlay(self, run, env, cmdline, inherit_tmpfiles = None):
        if self.profile_log is not None:
            self.env['CUDA_PROFILE_LOG'] = core.create_log(self.profile_log, run)

        if self.profile_log:
            log.log(self.collect, '{rsid} {runid} cuda/profiler {logfile}'.format(rsid=run.rspec.get_id(), runid=run.runid, logfile=self.env['CUDA_PROFILE_LOG']))
        else:
            log.log(self.collect, '{rsid} {runid} cuda/profiler cuda_profile_0.log'.format(rsid=run.rspec.get_id(), runid=run.runid))
        
        return super(CUDAProfilerOverlay, self).overlay(run, env, cmdline, inherit_tmpfiles)
