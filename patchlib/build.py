import config, mbox, data, apply, list, gitcmd, util
import shutil, errno, os, sys, json
from subprocess import check_call
from util import call_teed_output

def try_rmtree(path):
    try:
        shutil.rmtree(path)
    except OSError, (num, msg):
        if num != errno.ENOENT:
            raise

def try_to_build(series, working_dir, commit):
    try_rmtree(working_dir)

    check_call(['git', 'clone', '-sn', config.get_git_dir(), working_dir])
    check_call(['git', 'checkout', commit], cwd=working_dir)

    steps = []

    s, o = apply.apply_series(series, cwd=working_dir)
    steps.append(('apply', s, o))
    if s != 0:
        return s, steps

    cmds = config.get_buildbot()
    for step, cmd in cmds:
        s, o = call_teed_output(['/bin/sh', '-c', cmd], cwd=working_dir)
        steps.append((step, s, o))
        if s != 0:
            return s, steps

    return 0, steps

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    working_dir = config.get_working_dir()
    commit = gitcmd.get_sha1(config.get_master_branch())

    results = []

    for series in list.find_subseries(patches, args):
        result = series
        s, steps = try_to_build(series, working_dir, commit)
        result['buildbot'] = { 'status': s, 'steps': steps }
        results.append(result)

    try_rmtree(working_dir)
    util.replace_file(config.get_buildbot_json(),
                      json.dumps(results, indent=2,
                                 separators=(',', ': '),
                                 encoding='iso-8859-1'))
            
    
