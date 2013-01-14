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
from series import *
from subprocess import call
from util import call_teed_output
import os

def apply_patch(pathname, **kwds):
    return call_teed_output(['git', 'am', '--3way', pathname], **kwds)

def apply_pull_request(pull_request, **kwds):
    uri = pull_request['uri'].encode('ascii', errors='ignore')
    refspec = pull_request['refspec'].encode('ascii', errors='ignore')
    remotes = gitcmd.get_remotes()

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
   elif not 'mbox_path' in series:
       raise Exception('Cannot apply series: missing mbox')
   return apply_patch(mbox.get_real_path(series['mbox_path']), **kwds)

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    try:
        for series in patches:
            for msg in series['messages']:
                if msg['message-id'] == args.mid:
                    s, o = apply_series(series)
                    return s
    except Exception, e:
        print 'error: %s' % str(e)
        return 1

    print "Could not find patch series.  Try running `patches fetch'."
    return 1
            
