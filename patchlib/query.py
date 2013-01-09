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

import config, message, email.utils
import codecs, sys
from series import *

def encode(data):
    if type(data) == list:
        return map(encode, data)
    elif type(data) == tuple:
        return tuple(map(encode, data))
    elif type(data) == dict:
        new_dict = {}
        for key in data:
            new_dict[encode(key)] = encode(data[key])
        return new_dict
    elif type(data) in [str, unicode]:
        return unicode(data).encode('utf8')
    else:
        return data

def out(*args):
    if len(args) == 0:
        print
        return
    
    fmt = encode(args[0])
    args = args[1:]

    if len(args):
        print encode(fmt) % tuple(encode(args))
    else:
        print encode(fmt)

def match_email_address(lhs, rhs):
    lhs_name = lhs['name'].lower()
    lhs_email = lhs['email'].lower()

    rhs = rhs.lower()
    if lhs_name and lhs_name.find(rhs) != -1:
        return True

    if lhs_email and lhs_email.find(rhs) != -1:
        return True

    return False

def parse_query(query):
    terms = []

    i = 0
    term = ''
    while i < len(query):
        if query[i] == '"':
            start = i
            i += 1
            while i < len(query) and query[i] != '"':
                i += 1

            if i == len(query):
                raise Exception("Unterminated string '%s'" % query[start:])

            term += query[(start + 1):i]
        elif query[i] in ' \t':
            if term:
                terms.append(term)
                term = ''
        elif query[i] == '(':
            if term:
                terms.append(term)
                term = ''

            i += 1
            delta, subterms = parse_query(query[i:])
            terms.append(subterms)
            i += delta
        elif query[i] == ')':
            if term:
                terms.append(term)
                term = ''
            return i, terms
        else:
            term += query[i]
        i += 1

    if term:
        terms.append(term)
        term = ''

    return i, terms

def eval_messages(series, fn, scope):
    ret = False
    for message in series['messages']:
        if fn(message):
            ret = True
            if scope == 'any':
                break
        else:
            return False
    return ret

def eval_query_term(series, term, scope):
    ret = False

    if term.find(':') != -1:
        command, args = term.split(':', 1)
    else:
        command = None

    if command == 'status':
        status = args.lower()

        if status == 'broken':
            ret = is_broken(series)
        elif status == 'obsolete':
            ret = is_obsolete(series)
        elif status == 'pull-request':
            ret = is_pull_request(series)
        elif status == 'rfc':
            ret = is_rfc(series)
        elif status == 'unapplied':
            ret = not (is_broken(series) or
                       is_obsolete(series) or
                       is_pull_request(series) or
                       is_rfc(series) or
                       is_committed(series))
        elif status == 'committed':
            ret = is_committed(series)
        elif status == 'reviewed':
            ret = is_reviewed(series)
        else:
            raise Exception("Unknown status `%s'" % status)
    elif command == 'from':
        def fn(msg):
            return match_email_address(msg['from'], args)
        ret = eval_messages(series, fn, scope)
    elif term.startswith('to:'):
        def fn(msg):
            for to in msg['to'] + msg['cc']:
                if match_email_address(to, args):
                    return True
            return False
        ret = eval_messages(series, fn, scope)
    else:
        def fn(msg):
            return msg['subject'].lower().find(args.lower()) != -1
        ret = eval_messages(series, fn, scope)

    return ret, None

def eval_unary_query(series, terms, scope):
    if type(terms) == list:
        if len(terms) == 0:
            return ret, None
        elif terms[0] in ['any', 'all']:
            return eval_query(series, terms[1], terms[0])[0], terms[2:]
        elif terms[0] == 'not':
            return not eval_query(series, terms[1], scope)[0], terms[2:]
        else:
            return eval_query(series, terms[0], scope)[0], terms[1:]
    else:
        return eval_query_term(series, terms, scope)
    
def eval_binop_query(series, terms, scope):
    lhs, rest = eval_unary_query(series, terms, scope)
    if not rest:
        return lhs, rest

    if rest[0] == 'and':
        rhs, rest = eval_binop_query(series, rest[1:], scope)
        return lhs and rhs, rest
    elif rest[0] == 'or':
        rhs, rest = eval_binop_query(series, rest[1:], scope)
        return lhs or rhs, rest
    else:
        rhs, rest = eval_binop_query(series, rest, scope)
        return lhs and rhs, rest

def eval_query(series, terms, scope='any'):
    return eval_binop_query(series, terms, scope)

def find_subseries(patches, args):
    sub_series = []

    query = parse_query(' '.join(args.query))[1]
    for series in patches:
        if not eval_query(series, query)[0]:
            continue
    
        sub_series.append(series)

    return sub_series

def dump_notmuch_query(patches, args):
    import notmuch

    sub_series = find_subseries(patches, args)
    if not sub_series:
        return

    def fn(series):
        return 'id:"%s"' % series['messages'][0]['message-id']

    query = ' or '.join(map(fn, sub_series))

    db = notmuch.Database(config.get_notmuch_dir())
    q = notmuch.Query(db, query)

    tids = []
    for thread in q.search_threads():
        tids.append('thread:%s' % thread.get_thread_id())

    out(' or '.join(tids))

def dump_oneline_query(patches, args):
    for series in find_subseries(patches, args):
        out('%s %s', series['messages'][0]['message-id'],
            series['messages'][0]['subject'])

def dump_full_query(patches, args):
    for series in find_subseries(patches, args):
        msg = series['messages'][0]
        out('Message-id: %s', msg['message-id'])
        out('From: %s <%s>', msg['from']['name'], msg['from']['email'])
        for msg in series['messages']:
            ret = message.decode_subject_text(msg['subject'])
            out('   [%s/%s] %s', ret['n'], ret['m'], ret['subject'])
        out()
