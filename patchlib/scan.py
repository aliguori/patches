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

import notmuch, json, datetime, config
import gitcmd, message, mbox
import series as series_
from time import time
from ConfigParser import RawConfigParser
from email.header import decode_header
from email.utils import parseaddr
from util import *
import os

def days_to_seconds(value):
    return value * 24 * 60 * 60

def parse_email_address(value):
    name, mail = parseaddr(value)
    return { 'name': name, 'email': mail }

def parse_email_addresses(value):
    if value:
        if value.find(', ') == -1:
            return [ parse_email_address(value) ]
        else:
            return map(parse_email_address, value.split(', '))
    return []

def unique(lst):
    return list(set(lst))

##################################

def find_thread_leaders(q, then):
    oldest = then
    thread_leaders = {}

    for thread in q.search_threads():
        oldest = min(oldest, thread.get_oldest_date())

        top = list(thread.get_toplevel_messages())[0]
        if not message.is_patch(top):
            continue

        n, m, version, stripped_subject = message.parse_subject(top)
        if thread_leaders.has_key(stripped_subject) and version != None:
            new_version = max(version, thread_leaders[stripped_subject])
            thread_leaders[stripped_subject] = new_version
        else:
            thread_leaders[stripped_subject] = version

    return thread_leaders, oldest

def build_patch(commits, merged_heads, thread_leaders, msg, trees, leader=False):
    patch = {}

    sub = message.decode_subject(msg)
    stripped_subject = sub['subject']

    if sub.has_key('pull-request') and sub['pull-request']:
        parts = msg.get_message_parts()
        patch['pull-request'] = {}

        for line in parts[0].get_payload().split('\n'):
            stripped_line = line.strip()

            if stripped_line.startswith('git://'):
                uri, refspec = stripped_line.split(' ', 1)
                patch['pull-request']['uri'] = uri
                patch['pull-request']['refspec'] = refspec
            elif line.startswith('for you to fetch changes up to '):
                patch['pull-request']['head'] = line.rsplit(' ', 1)[1][:-1]
            elif line.startswith('---'):
                break

        if 'head' in patch['pull-request'] and 'uri' in patch['pull-request']:
            if patch['pull-request']['head'] in merged_heads:
                patch['pull-request']['commit'] = merged_heads[patch['pull-request']['head']]

    if sub['n'] == 0:
        # Patch 0/M is the cover letter
        patch['cover'] = True
    if leader and sub['version'] < thread_leaders[stripped_subject]:
        # If this is older than a version we've seen, the whole series is
        # obsolete.  We only look at the thread leader which is either the
        # cover letter or the very first patch.
        patch['obsolete'] = True
    elif commits.has_key(stripped_subject):
        # If there are multiple commits that have this subject, just pick
        # the first one.
        c = commits[stripped_subject]
        if type(c) == list:
            c = c[0]

        patch['commit'] = c['hexsha']
        patch['tree'] = c['branch']
        patch['url'] = trees[c['branch']] % patch['commit']
        patch['committer'] = c['committer']

    patch['tags'] = message.find_extra_tags(msg, leader)
    patch['subject'] = message.get_subject(msg)
    patch['message-id'] = msg.get_message_id()
    patch['cc'] = parse_email_addresses(message.get_header(msg, 'Cc'))
    patch['to'] = parse_email_addresses(message.get_header(msg, 'To'))
    if sub['rfc']:
        patch['rfc'] = sub['rfc']
    if sub.has_key('for-release'):
        patch['for-release'] = sub['for-release']
    if sub.has_key('tags'):
        patch['subject-tags'] = sub['tags']

    patch['from'] = parse_email_address(message.get_header(msg, 'From'))

    d = datetime.date.fromtimestamp(msg.get_date())
    patch['date'] = d.strftime('%Y-%m-%d')
    patch['full_date'] = msg.get_date()

    return patch

def fixup_pull_request(series, merged_heads):
    if 'head' in series['messages'][0]['pull-request']:
        return series

    if len(series['messages']) == 1:
        return series

    first_real_patch = series['messages'][-1]
    if ('commit' in first_real_patch and
        first_real_patch['commit'] in merged_heads):
        series['messages'][0]['pull-request']['commit'] = merged_heads[first_real_patch['commit']]

    return series
            

def build_patches(notmuch_dir, search_days, mail_query, trees):

    db = notmuch.Database(notmuch_dir)

    now = long(time())
    then = now - days_to_seconds(search_days)

    query = '%s (subject:PATCH or subject:PULL) %s..%s' % (mail_query, then, now)
    q = notmuch.Query(db, query)

    thread_leaders, oldest = find_thread_leaders(q, then)

    # A pull request may contain patches older than the posted commits.  That's
    # because a commit doesn't happen *after* the post like what normally
    # happens with a patch but rather the post happens after the commit.
    # There's no obvious way to handle this other than the hack below.

    # Give some extra time for pull request commits
    oldest -= (30 * 24 * 60 * 60)

    commits = gitcmd.get_commits(oldest, trees)
    merged_heads = gitcmd.get_merges(oldest)

    mbox.setup_mboxes()

    patches = []
    for thread in q.search_threads():
        top = list(thread.get_toplevel_messages())[0]

        if not message.is_patch(top):
            continue

        patch = build_patch(commits, merged_heads, thread_leaders,
                            top, trees, leader=True)

        patch_list = [ patch ]
        message_list = []

        if not message.is_cover(patch):
            message_list.append((top, patch['tags']))

        for reply in top.get_replies():
            # notmuch won't let us call get_replies twice so we have to do
            # everything in a single loop.

            # any first level replies are replies to the top level post.
            if not message.is_patch(reply):
                new_tags = message.find_extra_tags(reply, False)
                patch_list[0]['tags'] = message.merge_tags(patch_list[0]['tags'], new_tags)
            else:
                patch = build_patch(commits, merged_heads, thread_leaders, reply, trees)
                patch_list.append(patch)
                message_list.append((reply, patch['tags']))
    
        series = { 'messages': patch_list,
                   'total_messages': thread.get_total_messages() }

        if series_.is_pull_request(series):
            series = fixup_pull_request(series, merged_heads)
    
        message_list.sort(message.cmp_patch)

        m = message.parse_subject(top)[1]
        if len(message_list) != m:
            series['broken'] = True

        if (not series_.is_broken(series) and not series_.is_obsolete(series) and
            not series_.any_applied(series) and not series_.is_pull_request(series)):
            if message.is_cover(series['messages'][0]):
                tags = series['messages'][0]['tags']
            else:
                tags = {}

            series['mbox_path'] = mbox.generate_mbox(message_list, tags)
            series['mbox_hash'] = mbox.get_hash(series['mbox_path'])

        patches.append(series)

    return patches

def main(args):
    import json, config
    import data
    import hooks

    hooks.invoke('scan.pre')
    notmuch_dir = config.get_notmuch_dir()
    mail_query = config.get_mail_query()
    search_days = config.get_search_days()
    trees = config.get_trees()

    def sort_patch(a, b):
        return cmp(b['messages'][0]['full_date'], a['messages'][0]['full_date'])

    patches = build_patches(notmuch_dir, search_days, mail_query, trees)
    patches.sort(sort_patch)

    info = { 'version': data.VERSION,
             'patches': patches }

    replace_file(config.get_json_path(),
                 json.dumps(info, indent=2,
                            separators=(',', ': '),
                            encoding='iso-8859-1'))

    hooks.invoke('scan.post')

    return 0
