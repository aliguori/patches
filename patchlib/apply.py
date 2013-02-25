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

import config, mbox, gitcmd, data
from list import find_subseries
from series import *
from subprocess import call
from util import call_teed_output
import os

def apply_patch(pathname, **kwds):
    opts = [ '--3way' ]
    if 'signed-off-by' in kwds:
        opts.append('-s')
        del kwds['signed-off-by']
    if 'interactive' in kwds:
        opts.append('-i')
        del kwds['interactive']
    opts.append(pathname)
    return call_teed_output(['git', 'am'] + opts, **kwds)

def apply_pull_request(pull_request, **kwds):
    uri = pull_request['uri'].encode('ascii', errors='ignore')
    refspec = pull_request['refspec'].encode('ascii', errors='ignore')
    remotes = gitcmd.get_remotes(**kwds)

    if 'signed-off-by' in kwds:
        del kwds['signed-off-by']
    if 'interactive' in kwds:
        del kwds['interactive']

    if uri not in remotes:
        raise Exception('%s is not setup as a remote, please add a remote manually' % pull_request['uri'])

    remote = remotes[uri]

    s, o = call_teed_output(['git', 'fetch', remote], **kwds)
    if s != 0:
        return s, o

    return call_teed_output(['git', 'merge', '%s/%s' % (remote, refspec)], **kwds)

def apply_series(series, **kwds):
   if is_pull_request(series):
       return apply_pull_request(series['messages'][0]['pull-request'], **kwds)
   elif is_broken(series):
       raise Exception('Cannot apply series: series is either incomplete or improperly threaded.')
   elif not 'mbox_path' in series:
       raise Exception('Cannot apply series: missing mbox')
   return apply_patch(mbox.get_real_path(series['mbox_path']), **kwds)

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    kwds = {}
    if args.git_dir:
        kwds['cwd'] = args.git_dir
    if args.s:
        kwds['signed-off-by'] = True
    if args.interactive:
        kwds['interactive'] = True

    for series in find_subseries(patches, args):
        try:
            s, _ = apply_series(series, **kwds)
            if s:
                return s
        except Exception, e:
            print str(e)
            return 1

    return 0
            
