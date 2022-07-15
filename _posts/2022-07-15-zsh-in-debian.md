---
layout: post
title: Zsh in Debian
tags: [zsh, debian]
---

After installing some Flatpak package on my KDE Neon the application icon was not displaying neither
in the window header nor in the panel. I wanted to fix it and discovered that is related to `zsh`
package. Here is my troubleshooting path.

# Flatpak

Let's start with `Flatpak`. It's a way to distribute applications in Linux. It has some pros and
cons but I prefer it to install some proprietary apps and appps that are not supplied in the
distro repositories. After installing Telegram from Flatpak I noticed that the application icon
is missing in the task panel and in the window header. I started to search how Flatpak propagates
information about the app.

# Freedesktop

First of all such application resources as icons are stored in `share` directories. In Debian and
Ubuntu it's `/usr/local/share` and `/usr/share`. And there is an environments variable
`XDG_DATA_DIRS` which is a part of Freedesktop specification. Flatpak has its own directories for
application resources `$HOME/.local/share/flatpak/exports/share` and
`/var/lib/flatpak/exports/share`. And obviously it should add these directories into
`XDG_DATA_DIRS`. But they were not there.

# Again Flatpak

So how Flatpak updates `XDG_DATA_DIRS`. Arch wiki has a mention of it:

> Flatpak expects window managers to respect the XDG_DATA_DIRS environment variable to discover
> applications. This variable is set by the script /etc/profile.d/flatpak.sh. Updating the
> environment may require restarting the session.

This is it. `flatpak.sh` is executed from your `/etc/profile.d/` directory. But wait. This directory
is used by `/etc/profile` script. Basically it's the very first script that is executed by `bash`
when it's invoked.

# Zsh

But I use `zsh` not `bash`. I even use it as a login shell. Here is an excerpt from my
`/etc/passwd`:

```
dmisharo:x:1000:1000:Dmitry Misharov:/home/dmisharo:/usr/bin/zsh
```

`Zsh` doesn't source `/etc/profile`, it sources `zprofile` instead. And here is the most interesting
part. Unlike other popular Linux distributions Debian (and Ubuntu) supplies empty
`/etc/zsh/zprofile`:

```sh
# /etc/zsh/zprofile: system-wide .zprofile file for zsh(1).
#
# This file is sourced only for login shells (i.e. shells
# invoked with "-" as the first character of argv[0], and
# shells invoked with the -l flag.)
#
# Global Order: zshenv, zprofile, zshrc, zlogin
```

Fedora 36:

```sh 
#
# /etc/zprofile and ~/.zprofile are run for login shells
#

_src_etc_profile()
{
    #  Make /etc/profile happier, and have possible ~/.zshenv options like
    # NOMATCH ignored.
    #
    emulate -L ksh

    # source profile
    if [ -f /etc/profile ]; then
            source /etc/profile
    fi
}
_src_etc_profile

unset -f _src_etc_profile
```

Arch:

```sh
emulate sh -c 'source /etc/profile'
```

Debian developers intentionally do not source `/etc/profile` in `zprofile`:

> We need to keep so-called login-shell always as Bash if you don't want to drive
> yourself crazy.  Adding workarounds for all possible choices of so-called POSIX shell
> is just waste of resource.  If we make work around for zsh, then we need to do it for
> ksh, posh, ....  POSIX is no magic word for shells to be treated as equal since there
> are subtle differences.

# My solution

I ended up just copying Arch way and my `zprofile` sources `/etc/profile` via emulation.


References:
* <https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html>
* <https://wiki.archlinux.org/title/Flatpak#Add_Flatpak_.desktop_files_to_your_menu>
* <https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=983116#22>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/24)