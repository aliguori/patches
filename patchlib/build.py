#
# patches - QEMU Patch Tracking System
#
# Copyright IBM, Corp. 2013
#
# Authors:
#  Anthony Liguori <aliguori@us.ibm.com>
#
# This work is licensed under the terms of the GNU GPLv2 or later.
# See the COPYING file in the top-level directory.
#

from commands import getstatusoutput
from series import *
import os, shutil, json
import config, mbox, gitcmd, data

def try_to_build_series(series):
    if is_broken(series) or is_obsolete(series) or any_applied(series) or is_rfc(series):
        return None

    working_dir = config.get_build_working_dir()
    buildbot = {}

    commit = gitcmd.get_sha1(config.get_master_branch())

    s, o = getstatusoutput('git clone -s -n "%s" "%s"' % (config.get_git_wd_dir(),
                                                          working_dir))
    if s != 0:
        raise Exception(o)

    cwd = os.getcwd()
    os.chdir(working_dir)
    try:
        s, o = getstatusoutput('git checkout %s' % commit)
        if s != 0:
            raise Exception(o)

        commands = [ ('git-am', 'git am --3way %s' % mbox.get_real_path(series['mbox_path'])),
                     ('configure', './configure'),
                     ('make', config.get_make_command()) ]

        ret = { 'builds': True }
        for reason, command in commands:
            s, o = getstatusoutput(command)
            if s != 0:
                ret['builds'] = False
                ret['build-fail-reason'] = reason
                ret['build-fail-output'] = o
                break
    finally:
        os.chdir(cwd)

    shutil.rmtree(working_dir)

    return ret

def cache_lookup(series):
    mid = series['messages'][0]['message-id']
    base_dir = config.get_build_cache_dir()

    try:
        f = open('%s/mid-%s' % (base_dir, mid), 'r')
    except Exception, e:
        return None

    try:
        return json.loads(f.read())
    finally:
        f.close()

def cache_entry(series, result):
    base_dir = config.get_build_cache_dir()
    mid = series['messages'][0]['message-id']

    entry = '%s/mid-%s' % (base_dir, mid)
    tmp_entry = '%s/tmp-%s' % (base_dir, mid)

    try:
        os.makedirs(base_dir)
    except Exception, e:
        pass

    with open(tmp_entry, 'w') as f:
        f.write(json.dumps(result))
        f.flush()

    os.rename(tmp_entry, entry)

def try_to_build_patches(patches):
    new_patches = []

    for series in patches:
        entry = cache_lookup(series)

        if entry == None:
            entry = try_to_build_series(series)
            if entry != None:
                cache_entry(series, entry)

        if entry != None:
            series['buildbot'] = entry
        new_patches.append(series)

    return new_patches

def main(args):
    config.setup()

    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    print json.dumps(try_to_build_patches(patches), indent=2,
               separators=(',', ': '), encoding='iso-8859-1')

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
        
