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

from urllib2 import urlopen
from util import *
import config, mbox, data
import os

def main(args):
    if not args.url:
        fetch()
    else:
        fetch(args.url[0])

def fetch(url=None):
    if not url:
        url = config.get_fetch_url()

    if not url:
        raise Exception('URL not specified in config file and missing on command line')

    try:
        os.makedirs(config.get_mbox_path())
    except Exception, e:
        pass

    fp = urlopen(url)
    try:
        json_data = fp.read()
    finally:
        fp.close()

    patches = data.parse_json(json_data)

    print 'Fetched info on %d patch series' % len(patches)
    print 'Fetching mboxes...'

    for series in patches:
        if 'mbox_path' not in series:
            continue

        mbox_path = series['mbox_path']

        old_hash = mbox.get_hash(mbox_path)
        
        if 'mbox_hash' in series and series['mbox_hash'] == old_hash:
            continue

        print 'Fetching mbox for %s' % series['messages'][0]['subject']
        base, _ = url.rsplit('/', 1)

        fp = urlopen(base + '/' + series['mbox_path'])
        try:
            mbox_data = fp.read()
        finally:
            fp.close()

        replace_file(mbox.get_real_path(series['mbox_path']), mbox_data)

    replace_file(config.get_json_path(), json_data)
