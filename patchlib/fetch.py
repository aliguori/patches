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

def build_hash_table(patches):
    table = {}

    for series in patches['patches']:
        if 'mbox_hash' in series:
            table[series['mbox_path']] = series['mbox_hash']

    return table

def main(args):
    if not args.url:
        args.url = config.get_fetch_url()

    if not args.url:
        raise Exception('URL not specified in config file and missing on command line')
    url = args.url

    try:
        os.makedirs(config.get_mbox_path())
    except Exception, e:
        pass

    try:
        with open(config.get_json_path(), 'r') as fp:
            json_data = fp.read()
        old_patches = data.parse_json(json_data, full=True)
    except Exception, e:
        old_patches = { 'patches': [] }

    old_hash_table = build_hash_table(old_patches)

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

        if ('mbox_hash' in series and
            mbox_path in old_hash_table and
            old_hash_table[mbox_path] == series['mbox_hash']):
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
