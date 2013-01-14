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

import shutil, os, mailbox, hashlib
import config
from message import merge_tags, parse_tag

def setup_mboxes():
    try:
        os.makedirs(config.get_mbox_path())
    except Exception, e:
        pass

def add_tags(payload, tags):
    lines = []

    in_sob = False
    done = False
    for line in payload.split('\n'):
        tag = parse_tag(line, ['Signed-off-by'])
        if done:
            pass
        elif tag:
            in_sob = True

            key = tag.keys()[0]
            value = tag[key]

            # Don't duplicate tags
            if key in tags and value in tags[key]:
                continue
        elif in_sob:
            for key in tags:
                for val in tags[key]:
                    lines.append('%s: %s' % (key, val))
            in_sob = False
            done = True
        lines.append(line)

    return '\n'.join(lines)

def generate_mbox(messages, full_tags):
    mbox_dir = config.get_mbox_path()
    mid = messages[0][0].get_message_id()

    tmp_mbox_path = '%s/tmp-%s' % (mbox_dir, mid)
    mbox_path = '%s/mbox-%s' % (mbox_dir, mid)

    mbox = mailbox.mbox(tmp_mbox_path, create=True)
    for message, tags in messages:
        msg = message.get_message_parts()[0]
        msg.set_payload(add_tags(msg.get_payload(), merge_tags(full_tags, tags)))
        mbox.add(msg)
    mbox.flush()
    mbox.close()

    os.rename(tmp_mbox_path, mbox_path)

    return config.get_mbox_prefix() + ('mbox-%s' % mid)

def get_real_path(mbox_path):
    return '%s/%s' % (config.get_mbox_path(), mbox_path[len(config.get_mbox_prefix()):])

def get_hash(mbox_path):
    real_path = get_real_path(mbox_path)
    if not os.access(real_path, os.R_OK):
        return None

    with open(real_path, 'r') as fp:
        data = fp.read()

    # The first line of each message contains a date from the mailer which
    # changes whenever the mbox is regenerated.  Drop it from the hash
    # calculation
    def fn(line):
        return not line.startswith('From MAILER-DAEMON ')
    data = '\n'.join(filter(fn, data.split('\n')))

    h = hashlib.sha1()
    h.update(data)
    return h.hexdigest()
