---
title: Debugging system python scripts
tags: python, debug
---

I faced with broken `add-apt-repository` on my KDE Neon after upgrading to Ubuntu 22.04

```
aptsources.distro.NoDistroTemplateException: Error: could not find a distribution template for Neon/jammy
```

Though I knew that the issue was in `/etc/os-release` file I wanted to debug `add-apt-repository`
using [my favorite debugger]({filename}2020-05-24-best-python-debugger.md).

## Naive approach

It's a python script that comes with Ubuntu to manage repositories from PPA. If it's a python script
it can be debugged with `pudb`. But first of all we need to install it:

1. Create a fresh virtual environment:

        virtualenv ~/venvs/pudb
        Created virtual environment CPython3.10.4.final.0-64 in 216ms
        creator CPython3Posix(dest=/home/misharov/venvs/pudb, clear=False, no_vcs_ignore=False, global=False)
        seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/home/misharov/.local/share/virtualenv)
            added seed packages: pip==22.0.2, setuptools==59.6.0, wheel==0.37.1
        activators BashActivator,CShellActivator,FishActivator,NushellActivator,PowerShellActivator,PythonActivator
        

2. Activate it:

        source /home/misharov/venvs/pudb/bin/activate

3. Install `pudb`:

        pip install pudb

4. Run `add-apt-repository` in the debug mode. The naive approach would be running the script like
this:

        python -m pudb /usr/bin/add-apt-repository


It will be executed until you will get the following error:

```text
ModuleNotFoundError: No module named 'apt_pkg'
```

Ouch, the naive approach was wrong. Our virtual environment is not aware about system installed
packages. In Ubuntu 22.04 system python packages are installed in the following paths:

```sh
python3 -c 'import site; print(site.getsitepackages())'
['/usr/local/lib/python3.10/dist-packages', '/usr/lib/python3/dist-packages', '/usr/lib/python3.10/dist-packages']
```

`apt_pkg` can be found in `/usr/lib/python3/dist-packages`

## The right way

Someone would propose to install `pudb` along with system python packages but it might even break
the system python. Therefore never run `sudo pip install`! There is a better way. `virtualenv`
can create a virtual environment that uses system packages:

```sh
virtualenv --system-site-packages ~/venvs/pudb
created virtual environment CPython3.10.4.final.0-64 in 114ms
  creator CPython3Posix(dest=/home/misharov/venvs/pudb, clear=False, no_vcs_ignore=False, global=True)
  seeder FromAppData(download=False, pip=bundle, setuptools=bundle, wheel=bundle, via=copy, app_data_dir=/home/misharov/.local/share/virtualenv)
    added seed packages: pip==22.0.2, setuptools==59.6.0, wheel==0.37.1
  activators BashActivator,CShellActivator,FishActivator,NushellActivator,PowerShellActivator,PythonActivator
```

New packages will be installed into the virtual environment and system packages will be accounted
as well. After activation and installation `pudb` we can run `add-apt-repository` in the debug mode.

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/25)
