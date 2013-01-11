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

from ConfigParser import RawConfigParser
import os.path, email.utils, os

ini = RawConfigParser()
config_filename = None

def setup(filename):
    global config_filename

    if not filename:
        dirs = os.getcwd().split('/')
        for i in range(0, len(dirs)):
            if i:
                path = '/'.join(dirs[0:-i])
            else:
                path = '/'.join(dirs)

            path += '/.patchesrc'

            if os.access(path, os.R_OK):
                filename = path
                break

        if not filename:
            filename = os.path.expanduser('~/.patchesrc')
    elif filename[0] != '/':
        filename = os.getcwd() + '/' + filename

    config_filename = filename
    ini.read(filename)

def get_list_tag():
    if ini.has_option('scan', 'list_tag'):
        return ini.get('scan', 'list_tag')
    return ''

def get_git_dir():
    if ini.has_option('scan', 'git_dir'):
        return ini.get('scan', 'git_dir') + '/.git'
    return get_patches_dir() + '/git'

def get_git_wd_dir():
    return ini.get('scan', 'git_dir')

def get_master_branch():
    return ini.get('scan', 'master_branch')

def get_make_command():
    return ini.get('build', 'make')

def get_notmuch_dir():
    if ini.has_option('scan', 'notmuch_dir'):
        return ini.get('scan', 'notmuch_dir')
    return get_patches_dir() + '/notmuch'

def get_notified_dir():
    if ini.has_option('options', 'notified_dir'):
        return ini.get('options', 'notified_dir')
    return get_patches_dir() + '/notified'

def get_patches_dir():
    if ini.has_option('options', 'patches_dir'):
        return ini.get('options', 'patches_dir')
    return config_filename.rsplit('/', 1)[0] + '/.patches'

def get_json_path():
    if ini.has_option('options', 'json_path'):
        return ini.get('options', 'json_path')
    return get_patches_dir() + '/public/patches.json'

def get_mail_query():
    if ini.has_option('scan', 'mail_query'):
        return ini.get('scan', 'mail_query')
    return ''

def get_search_days():
    if ini.has_option('scan', 'search_days'):
        return int(ini.get('scan', 'search_days'))
    return 30

def get_trees():
    trees = {}
    for branch, uri in ini.items('trees'):
        trees[branch] = uri
    return trees

def get_smtp_server():
    return ini.get('notify', 'smtp_server')

def get_default_sender():
    return ini.get('notify', 'default_sender')

def get_committer_whitelist():
    if ini.has_option('notify', 'whitelist'):
        wl = ini.get('notify', 'whitelist')
        if wl.find(';') == -1:
            return [wl]
        return wl.split(';')
    else:
        return [email.utils.parseaddr(get_default_sender())[0]]

def get_build_cache_dir():
    if ini.has_option('build', 'cache_dir'):
        return ini.get('build', 'cache_dir')
    return get_patches_dir() + '/build-cache'

def get_build_working_dir():
    if ini.has_option('build', 'working_dir'):
        return ini.get('build', 'working_dir')
    return get_patches_dir() + '/git-working'

def get_mbox_path():
    if ini.has_option('apply', 'mbox_path'):
        return ini.get('apply', 'mbox_path')
    return get_patches_dir() + '/public/patches'

def get_mbox_prefix():
    if ini.has_option('apply', 'mbox_prefix'):
        return ini.get('apply', 'mbox_prefix')
    return 'patches/'

def get_hook(name):
    if ini.has_option('hooks', name):
        return ini.get('hooks', name)
    return None

def parse_list(value):
    if value.find(';') == -1:
        return [value]
    return value.split(';')

def get_notify_events():
    if ini.has_option('notify', 'events'):
        return parse_list(ini.get('notify', 'events'))
    return []

def get_fetch_url():
    if ini.has_option('fetch', 'url'):
        return ini.get('fetch', 'url')
    return None

EMAIL_TAGS = ['Reviewed-by', 'Tested-by', 'Acked-by', 'Nacked-by',
              'Reported-by', 'Signed-off-by', 'Rejected-by']

def get_email_tags():
    if ini.has_option('options', 'email-tags'):
        return parse_list(ini.get('options', 'email-tags'))
    return EMAIL_TAGS

def get_nntp_server():
    return ini.get('nntp', 'server')

def get_nntp_group():
    return ini.get('nntp', 'group')

def set(section, item, value):
    if not ini.has_section(section):
        ini.add_section(section)
    ini.set(section, item, value)
