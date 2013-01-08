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

import os

def replace_file(filename, data):
    backup = "%s~" % filename
    if filename.find('/') != -1:
        parts = filename.split('/')
        parts[-1] = '.#' + parts[-1]
        tmp_filename = '/'.join(parts)
    else:
        tmp_filename = ".#%s" % filename

    try:
        with open(filename, 'r') as infp:
            with open(backup, 'w') as outfp:
                outfp.write(infp.read())
    except Exception, e:
        pass

    with open(tmp_filename, 'wb') as fp:
        fp.write(data)

    os.rename(tmp_filename, filename)
