---
layout: post
title: Kodi add-on testing
tags: [kodi, add-on, testing]
---
Ok, you develop a Kodi add-on and you would like to have CI for your code. What options do you have?
How Kodi add-ons can be tested? And how to configure a CI for a Kodi add-on code? Let me share my
experience.

## Unit tests

According to the testing pyramid the bulk of your tests are unit tests:

{:refdef: style="text-align: center;"}
![diagram 1](/assets/img/2021-03-03-kodi-addon-testing-1.png)
{: refdef}
{:refdef: style="text-align: center;"}
*diagram 1*
{: refdef}

The problem with Kodi is its python API is accessible only within Kodi runtime. For example, if you
need to get the addon info you can use the following code:

```python
import xbmcaddon

xbmcaddon.Addon().getAddonInfo("version") 
```

`xbmcaddon` is a python interface for Kodi C++ code and it cannot be installed in your virtual
environment. You have to mock it. Combining python mocking library `unittest.mock` and
[@RomanVM](https://github.com/RomanVM)'s Kodi stubs you can create some unit tests. But I must
admit that it might be not so trivial to write them. Your tests will be as good as your mocks are.
You might come to the situation when test maintenance takes more time than working on the add-on's
code. In my opinion, it makes sense to write unit tests for the code that doesn't use Kodi python
API. It might be various helpers, utilities, or really simple functions and classes that don't
require to mock a lot of side effects.
Of course, I highly recommend using `pytest` as a testing library. It's really the best tool for
test development. Moreover, it doesn't matter where your tests are located in the testing pyramid.

## Integration tests

Integration tests assume that your code will be tested in the running Kodi instance. Now we need to
solve the following problems to write the automation:

* we need a running Kodi and we should be able to specify its version;
* we should be able to install a development version of the testing add-on;
* we need to have an interface to interact with Kodi automatically;
* we should be able to check expected results.

### Kodi setup

I have a strong opinion that containers ideally fit this task and other similar tasks such as
UI testing of web applications. In my previous post [Conkodi]({% post_url 2021-02-14-conkodi %})
I explained how to create and run a container with Kodi. Using this container image we can configure
our setup stage in pytest's `conftest.py`:

```python
import subprocess

import pytest

# it's just a helping function for podman CLI
def podman(*args):
    subprocess.run(["podman"] + list(args), stdout=subprocess.DEVNULL)

# we want to have running Kodi container during whole testing session
@pytest.fixture(scope="session")
def run_kodi():
    # remove containers from previous run 
    podman("rm", "-f", "kodi")
    podman(
        "run",
        "--detach", # run a container in the background
        "--name=kodi", # with the name "kodi"
        # make various ports accessible for the host
        "--publish=8080:8080", # Kodi JSON RPC listens to this port
        "--publish=5999:5999", # this port needs accessing VNC server of the container
        "--publish=9777:9777/udp", # Kodi EventServer listens to this port
        "quay.io/quarck/conkodi:19", # the name and the tag of the container image with Kodi
    )
    yield
    podman("stop", "kodi") # teardown, stop the container
```

### Add-on installation

Kodi add-ons can be installed only via the UI. You need to find a zip archive in the filesystem and
click several buttons in Kodi. There is no CLI or API that allows the installation of an add-on.
What can we do here? First of all, let's make a small study of what happens when you install a Kodi
add-on. After the installation, the add-on archive is unpacked into `addons` directory. Besides, new
entries are created in the databases `Addons33.db` and `Textures13.db`. Knowing these facts we can
setup our container in such a way that Kodi will have the add-on installed. We can mount host
directories with the code of the add-on and the prepared database in a Kodi container. Let's update
the code from the previous paragraph:

```python
import shutil
import subprocess

import pytest

def podman(*args):
    subprocess.run(["podman"] + list(args), stdout=subprocess.DEVNULL)

@pytest.fixture(scope="session")
def build_plugin():
    # Here we copy a development version of the add-on into the directory with where all Kodi
    # add-ons are stored
    shutil.copytree("/dir/with/addon/code", "/dir/with/addons/some.addon")
    yield
    shutil.rmtree("/dir/with/addons/some.addon")

@pytest.fixture(scope="session")
def run_kodi_container(build_plugin):
    podman("rm", "-f", "kodi")
    podman(
        "run",
        "--detach",
        "--name=kodi",
        "--publish=8080:8080",
        "--publish=5999:5999",
        "--publish=9777:9777/udp",
        # Mounting a directory with a development version of the add-on 
        "--volume=/some/host/dir/addons/:/home/kodi/.kodi/addons",
        # Mounting a directory with prepared databases
        "--volume=/some/host/dir/Database/:/home/kodi/.kodi/userdata/Database",
        "quay.io/quarck/conkodi:19",
    )
    yield
    podman("pod", "stop", "kodi")
```

### Kodi JSON RPC

Ok, we have a running container with Kodi and installed add-on and now it would be nice to have an
API for making various actions in Kodi. And there is some! Kodi provides JSON RPC API that allows
you to get a list of the items of a directory, execute addons with parameters, get properties of GUI
windows, and so on and so on. There are several python clients and I stopped my choice on
`kodi-json`. Virtually it supports all available methods. Let me demonstrate how it can be used:

```python
from kodijson import Kodi

# Instantiate a Kodi object
kodi = Kodi("http://127.0.0.1:8080")
# Get list of items of the root directory of some addon
kodi.Files.GetDirectory(directory="plugin://some.addon")
```

We could even create a fixture in our test suite:

```python
import pytest
from kodijson import Kodi

@pytest.fixture(scope="session")
def kodi(run_kodi_container):
    return Kodi(JSON_RPC_URL)
```

And then use it in tests:

```python
EXPECTED_ROOT_DIR = [
    {
        "file": "plugin://some.addon/some_item/",
        "filetype": "file",
        "label": "Some item",
        "type": "unknown",
    },
    {
        "file": "plugin://some.addon/some_dir/",
        "filetype": "directory",
        "label": "Some dir",
        "type": "unknown",
    },
]

def test_root_dir(kodi):
    response = kodi.Files.GetDirectory(directory="plugin://some.addon")
    assert ROOT_DIR == resp["result"]["files"]
```

That's the basics of the integration tests of a Kodi add-on. Despite JSON RPC doesn't allow
you to do everything you can do via GUI in most cases it will be enough. You can even send keyboard
button events and navigate through the UI but it might be error-prone.

References:

* <https://kodi.tv>
* <https://kodi.wiki/view/JSON-RPC_API/v12>
* <https://github.com/jcsaaddupuy/python-kodijson>
* <https://github.com/quarckster/conkodi>
* <https://quay.io/repository/quarck/conkodi?tab=tags>
* <https://podman.io>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/11)
