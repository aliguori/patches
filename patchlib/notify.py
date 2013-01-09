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

import email.message, email.utils
import os, smtplib, time
import config, data
from series import *
from email.header import Header

def format_addr(addr):
    name = addr['name']

    # This seems like a python bug to me...
    if name.encode('ascii', errors='replace') != name:
        name = str(Header().append(addr['name']))

    return email.utils.formataddr((name, addr['email']))

def encode_address_list(addrs):
    return ', '.join(map(format_addr, addrs))

def try_to_send(args, notified_dir, sender, message, payload):
    mid = message['message-id']
    if os.access(notified_dir + '/mid/' + mid, os.F_OK):
        return

    if not args.dry_run:
        f = open(notified_dir + '/mid/' + mid, 'w')
        f.flush()
        f.close()

    msg = email.message.Message()

    receipents = [ message['from'] ]
    receipents += message['to']
    receipents += message['cc']
    receipents = map(format_addr, receipents)

    msg['From'] = sender
    msg['Subject'] = 'Re: %s' % message['subject']
    msg['Cc'] = encode_address_list(message['cc'])
    msg['To'] = encode_address_list([ message['from'] ] + message['to'])
    msg['In-Reply-To'] = '<%s>' % message['message-id']
    msg['Date'] = email.utils.formatdate()
    msg.set_payload(payload)

    if not args.dry_run and not args.fake:
        sent = False
        for i in range(10):
            try:
                s = smtplib.SMTP(config.get_smtp_server())
                s.sendmail(sender, receipents, msg.as_string())
                s.quit()
                sent = True
                break
            except:
                time.sleep(1)

        if not sent:
            raise

    print msg.as_string()
    print '-' * 80

def send_response(args, notified_dir, message, committer):
    sender = email.utils.formataddr((committer['name'],
                                     committer['email']))

    try_to_send(args, notified_dir, sender, message, '''Thanks, applied.

Regards,

%s''' % committer['name'])

def send_pull_response(args, notified_dir, message, committer):
    if committer == None:
        sender = config.get_default_sender()
        name, _ = email.utils.parseaddr(sender)

        try_to_send(args, notified_dir, sender, message, '''Pulled, thanks.

N.B.  This note may be extraneous because the pull request was sent by a
version of git older than 1.7.9 making the pull request ambigious.  Please
consider upgrading to a newer version of git.

Regards,

%s''' % name)
    else:
        sender = email.utils.formataddr((committer['name'],
                                         committer['email']))

        try_to_send(args, notified_dir, sender, message, '''Pulled, thanks.

Regards,

%s''' % committer['name'])

def send_response_not_applies(args, notified_dir, series):
    git_am = series['git-am-error']
    git_am = git_am.replace('\n', '\n    ')
    sender = config.get_default_sender()
    
    try_to_send(args, notified_dir, sender, series['messages'][0],
                '''Hi,

This is an automated message generated from the QEMU Patches.
Thank you for submitting this patch.  This patch no longer applies to qemu.git.

This may have occurred due to:
 
  1) Changes in mainline requiring your patch to be rebased and re-tested.

  2) Sending the mail using a tool other than git-send-email.  Please use
     git-send-email to send patches to QEMU.

  3) Basing this patch off of a branch that isn't tracking the QEMU
     master branch.  If that was done purposefully, please include the name
     of the tree in the subject line in the future to prevent this message.

     For instance: "[PATCH block-next 1/10] qcow3: add fancy new feature"

  4) You no longer wish for this patch to be applied to QEMU.  No additional
     action is required on your part.

Nacked-by: QEMU Patches <aliguori@us.ibm.com>

Below is the output from git-am:

    %(git_am)s

''' % { 'git_am': git_am })

def notify_patches(args, patches, notified_dir, whitelist):
    events = config.get_notify_events()

    for series in patches:
        if is_obsolete(series) or is_rfc(series) or has_subject_tags(series):
            pass
        elif is_pull_request(series):
            if 'pulled' not in events:
                continue

            committed = is_committed_in_branch(series, config.get_master_branch())
            pr = series['messages'][0]['pull-request']
            committer = None

            if 'commit' in pr:
                if pr['commit']['committer']['name'] not in whitelist:
                    continue
                commit = pr['commit']['commit']
                committer = pr['commit']['committer']
            elif committed:
                if 'head' in pr:
                    # This can happen because of a committer merging master
                    # back in their topic branch.  It can also happen because
                    # the branch was changed before merging without sending a
                    # new pull request.   These are bad practices
                    # so let's not encourage them further.
                    continue
                else:
                    # This was a pull request generated with a version of
                    # git-send-email before 1.7.9.  It's very hard to find
                    # the merge commit so we assume the first patch commit
                    # for tracking purposes.
                    # We can't find the actual committer though.

                    for message in series['messages']:
                        if 'cover' in message and message['cover']:
                            continue
                        commit = message['commit']
                        break
            else:
                continue

            if os.access(notified_dir + '/commit/' + commit, os.F_OK):
                continue

            if not args.dry_run:
                f = open(notified_dir + '/commit/' + commit, 'w')
                f.flush()
                f.close()

            send_pull_response(args, notified_dir, series['messages'][0], committer)
        elif is_broken(series):
            # Pull requests are often 'broken' because not everyone marks the
            # 0ths patch correctly.  Be a little more tolerant of broken pull
            # requests but certainly not patch series.
            pass
        elif is_committed(series):
            if 'committed' not in events:
                continue

            first_commit = None

            for patch in series['messages']:
                if "commit" in patch:
                    first_commit = patch
                    break

            if first_commit == None:
                raise Exception("Internal error")

            commit = first_commit['commit']

            if first_commit['committer']['name'] not in whitelist:
                continue

            if os.access(notified_dir + '/commit/' + commit, os.F_OK):
                continue

            if not args.dry_run:
                f = open(notified_dir + '/commit/' + commit, 'w')
                f.flush()
                f.close()

            send_response(args, notified_dir, series['messages'][0], first_commit['committer'])
        elif series.has_key('applies') and not series['applies']:
            if 'not-applied' not in events:
                continue
            send_response_not_applies(args, notified_dir, series)
            
            
def main(args):
    import config

    notified_dir = config.get_notified_dir()

    try:
        os.makedirs(notified_dir + '/commit')
    except Exception, e:
        pass

    try:
        os.makedirs(notified_dir + '/mid')
    except Exception, e:
        pass

    if args.smtp_server != None:
        config.set('notify', 'smtp_server', args.smtp_server)
    if args.sender != None:
        config.set('notify', 'default_sender', args.sender)
    if args.events != None:
        config.set('notify', 'events', ';'.join(arg.events))

    with open(config.get_json_path(), 'rb') as fp:
        patches = data.parse_json(fp.read())

    notify_patches(args, patches, notified_dir, config.get_committer_whitelist())

    return 0
