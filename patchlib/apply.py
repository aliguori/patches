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
import os

def apply_patch(pathname):
    os.execlp('git', 'git', 'am', '--3way', pathname)

def apply_pull_request(pull_request):
    uri = pull_request['uri'].encode('ascii', errors='ignore')
    refspec = pull_request['refspec'].encode('ascii', errors='ignore')
    remotes = gitcmd.get_remotes()

    if uri not in remotes:
        print '%s is not setup as a remote, please add a remote manually' % pull_request['uri']
        return 1

    remote = remotes[uri]

    s = call(['git', 'fetch', remote])
    if s != 0:
        return s

    return call(['git', 'merge', '%s/%s' % (remote, refspec)])

def main(args):
    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    for series in patches:
        for msg in series['messages']:
            if msg['message-id'] == args.mid:
                if is_pull_request(series):
                    return apply_pull_request(series['messages'][0]['pull-request'])
                elif not 'mbox_path' in series:
                    print 'Cannot apply series: missing mbox'
                    return 1
                return apply_patch(mbox.get_real_path(series['mbox_path']))

    print "Could not find patch series.  Try running `patches fetch'."
    return 1
            
