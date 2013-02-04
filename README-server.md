Setting up a New Patch Database
-------------------------------

To setup a new patch database, you need to create a `~/.patchesrc` file with
at least the following sections:

    [scan]
    # The tag that mailman prepends to all messages.  This can be omitted
    # if the list isn't configured to do this.
    list_tag=Qemu-devel
    
    # The git repository to use to determine which patches are committed.
    # It must have remotes configured for all subtrees and must be kept up
    # to date independently of patches.  See hooks.scan.pre
    git_dir=/home/aliguori/patches/qemu.git
    # The refspec that's considered the 'master' branch
    master_branch=origin/master
    
    # The notmuch database that holds mail.  It must be kept up to date
    # independently of patches
    notmuch_dir=/home/aliguori/patches/mail
    # The query used to identify mail.  This is meant to allow a single
    # notmuch database to be used for multiple lists.
    mail_query=to:qemu-devel@nongnu.org
    # The number of days to limit the analysis to.
    search_days=30
    
    [hooks]
    # A program to execute before 'patches scan' starts.  This can be used
    # to update notmuch and to fetch new commits from git.
    scan.pre=/home/aliguori/.patches/hooks/scan-pre
    
    # All subtrees need an entry in the [trees] section.  The key is the
    # refspec within the git repository for the subtree and the value is
    # a URI to be interpolated with the git commit hash for a web-view URL
    [trees]
    origin/master=http://git.qemu.org/?p=qemu.git;a=commit;h=%s
    stefanha/trivial-patches=http://github.com/stefanha/qemu/commit/%s
    ...

After patches is configured, you can simply run `patches scan` to create
the database.  The results will be stored in `~/.patches/public` which can
then be published via HTTP or FTP.
