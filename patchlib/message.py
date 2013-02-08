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

import config
from email.header import decode_header

def get_header(msg, name):
    value = u''

    # notmuch's Message.get_header() doesn't handle chunked encoded headers
    # correctly so we fix it here.
    header = msg.get_header(name)
    if header.find('=?') != -1:
        for chunk, encoding in decode_header(header):
            value += unicode(chunk, encoding or 'ascii')
    else:
        value = unicode(header)

    return value

def get_subject(msg):
    list_tag = u'[%s] ' % config.get_list_tag();
    subject = get_header(msg, 'Subject')
    if subject.startswith(list_tag):
        subject = subject[len(list_tag):].strip()
    return subject

def find_and_split(haystack, needle):
    index = haystack.find(needle)
    if index == -1:
        return haystack, ''
    else:
        return haystack[0:index], haystack[index + len(needle):]

def is_digit(ch):
    return ch in '0123456789'

def parse_subject(msg):
    ret = decode_subject(msg)
    return ret['n'], ret['m'], ret['version'], ret['subject']

def decode_subject(msg):
    subject = get_header(msg, 'Subject')
    return decode_subject_text(subject)

def decode_subject_text(subject):
    ret = { 'n': 1, 'm': 1, 'version': 1, 
            'patch': False, 'rfc': False }
    patch_tags = []

    while len(subject) and subject[0] == '[':
        bracket, subject = find_and_split(subject[1:], ']')
        subject = subject.lstrip()

        if bracket:
            words = map(unicode.upper, bracket.split(' '))

            for word in words:
                if not word:
                    continue

                if word.startswith('PATCH') and word != 'PATCH':
                    # It's pretty common for people to do PATCHv2 or
                    # other silly things.  Try our best to handle that.
                    word = word[5:]
                    ret['patch'] = True

                index = word.find('/')
                if index != -1 and is_digit(word[0]) and is_digit(word[index + 1]):
                    ret['n'], ret['m'] = map(int, word.split('/', 1))
                elif word[0] == 'V' and is_digit(word[1]):
                    try:
                        ret['version'] = int(word[1:])
                    except Exception, e:
                        pass
                elif word.startswith('FOR-') and is_digit(word[4]):
                    ret['for-release'] = word[4:]
                elif is_digit(word[0]) and word.find('.') != -1:
                    ret['for-release'] = word
                elif word in ['RFC', '/RFC']:
                    ret['rfc'] = True
                elif word in ['PATCH']:
                    ret['patch'] = True
                elif word in ['PULL']:
                    ret['pull-request'] = True
                    ret['patch'] = True
                elif word == config.get_list_tag().upper():
                    pass
                else:
                    patch_tags.append(word)

    if patch_tags:
        ret['tags'] = patch_tags

    ret['subject'] = subject

    return ret

def is_capital(ch):
    return ch >= 'A' and ch <= 'Z'

def is_lower(ch):
    return ch >= 'a' and ch <= 'z'

def format_tag_name(key):
    return key[0].upper() + key[1:].lower()

def parse_tag(line, extra_tags=[]):
    if not line:
        return None

    i = 0
    if not is_capital(line[i]):
        return None

    i += 1
    while i < len(line) and (is_capital(line[i]) or
                             is_lower(line[i]) or
                             line[i] == '-'):
        i += 1

    if i == len(line) or line[i] != ':':
        return None

    key = format_tag_name(line[0:i])
    value = line[i + 1:].strip()

    if key not in (config.get_email_tags() + extra_tags) or not value:
        return None

    return { key: [value] }

def merge_tags(lhs, rhs):
    val = {}
    for key in lhs:
        if key in ['Message-id']:
            continue
        val[key] = lhs[key]

    for key in rhs:
        if key in ['Message-id']:
            continue
        if key not in val:
            val[key] = []
        for tag in rhs[key]:
            if tag not in val[key]:
                val[key].append(tag)

    return val
    

def find_extra_tags(msg, leader):
    extra_tags = {}

    parts = msg.get_message_parts()
    for line in parts[0].get_payload(decode=True).split('\n'):
        line = line.strip()

        if line == '---' or line.startswith('diff '):
            break

        tag = parse_tag(line)
        if tag:
            extra_tags = merge_tags(extra_tags, tag)

    if not leader:
        for reply in msg.get_replies():
            new_tags = find_extra_tags(reply, leader)
            extra_tags = merge_tags(extra_tags, new_tags)

    return extra_tags

def cmp_patch(a, b):
    a_n = parse_subject(a[0])[0]
    b_n = parse_subject(b[0])[0]

    return cmp(a_n, b_n)

def is_cover(msg):
    if msg.has_key('cover') and msg['cover']:
        return True
    return False

def is_patch(msg):
    ret = decode_subject(msg)
    return ret['patch']
    
