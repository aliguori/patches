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

import json

VERSION = 1

def parse_json(data):
    info = json.loads(data, encoding='utf8')
    if info['version'] != VERSION:
        raise Exception("Unsupported JSON version %s" % info["version"])
    return info['patches']
