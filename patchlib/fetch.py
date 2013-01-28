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
import os, json

def main(args):
    if not args.url:
        fetch()
    else:
        fetch(args.url)

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

    full_patches = data.parse_json(json_data, full=True)
    patches = full_patches['patches']

    print 'Fetched info on %d patch series' % len(patches)
    if 'links' in full_patches:
        print 'Fetching links...'

        mids = {}
        for name in full_patches['links']:
            url = full_patches['links'][name]

            fp = urlopen(url)
            try:
                link_data = fp.read()
            finally:
                fp.close()

            builds = data.parse_json(link_data, full=True)
            for series in builds['patches']:
                if 'buildbot' not in series:
                    continue

                mid = series['messages'][0]['message-id'] 
                if mid not in mids:
                    mids[mid] = {}
                mids[mid][name] = series['buildbot']
                mids[mid][name]['owner'] = builds['owner']

        for series in patches:
            mid = series['messages'][0]['message-id']
            if mid in mids:
                series['buildbots'] = mids[mid]

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

    json_data = json.dumps(full_patches, indent=2,
                           separators=(',', ': '),
                           encoding='iso-8859-1')

    replace_file(config.get_json_path(), json_data)
