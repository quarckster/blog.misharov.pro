---
layout: post
title: Evolution of UI testing
tags: [pytest, selenium, containers, pytest-xdist, ci]
---
Web UI testing is a tricky thing in many aspects. They requires many dependencies, they are slow and
they are often flaky. In this post I would like to share my web UI testing experience on an example
of one python library.

## widgetastic.patternfly4

I maintain a library that Red Hat uses for web UI testing. It's called `widgetastic.patternfly4` and
you can find it on Github. It abstracts some components from Patternfly design system.

## CI

Every good library should have tests otherwise we cannot even know if something work there.
Therefore PR testing is a "must have" nowadays. There are many cloud base CI systems and I chose
Travis CI. I've already had some experience with it and that was a main reason of my choice.
All of these CI services give you a virtual machine where you can run your code. In the most of
cases preinstalled software is enough. The real fun begins when you need to install and setup
something that is missing.

This is a case of `widgetastic.patternfly4`. It has `selenium` in the dependencies. It means that
before a test session starts we need to install a browser (Chrome or Firefox) and an appropriate
webdriver (geckodriver or chromedriver). The very straightforward solution would be installing all
that stuff during the PR testing. My Travis CI config looked something like this at that time:

```yaml
# Travis CI provides an easy way to install a browser
addons:
  firefox: latest
language: python
...
stage: test
env: BROWSER=firefox
before_install:
  - pip install -U setuptools pip
  - pip install flake8 pytest pytest-cov coveralls
  # I found an utility that downloads a right version of the webdriver
  - pip install webdriverdownloader
  - webdriverdownloader firefox
install: python setup.py install
script:
  - flake8 src testing --max-line-length=100
  - py.test -v --cov widgetastic_patternfly4 --cov-report term-missing
...
```

## Containers

The aforementioned approach didn't work well. First it takes time to install all dependencies.
Second `webdriverdownloader` was buggy and often tests couldn't even start. Another issue was in the
way how browsers run. Obviously CI machine doesn't need any GUI therefore we have to run both Chrome
and Firefox in headless mode. In this mode the browser renders the pages in the memory. It turned
out that test results may differ significantly.

The solution was on the surface. Containers was already the industry standard and they perfectly fit
to my problem. Now I'm thinking why I didn't come up to it from the beginning 😅. So instead of
installing dependencies during PR testing it's better to pack everything what we need in a one
container image. I created such image and pushed it to `quay.io` image registry. After that CI
config became into:

```yaml
language: python
...
stage: test
# here we start docker service
services:
  - docker
env: BROWSER=firefox
before_install:
  # The container has Selenium standalone running. In the tests we can use Remote webdriver to
  # connect to it. Moreover we can even have X server inside and run browsers in regular way.
  - docker run -d -p 4444:4444 -v /dev/shm:/dev/shm quay.io/redhatqe/selenium-standalone
install:
  - pip install -U setuptools pip wheel
  - pip install pytest pytest-cov codecov
  - python setup.py install
script: pytest -v --no-cov-on-fail --cov=widgetastic_patternfly4
...
```

## Can I do better?

I was satisfied for while and switched to other projects. In the meantime the library was growing.
More components were added and tests as well. A session of 116 tests took more than **20** minutes.
I wanted to do something about it. It needs to know that tests are run sequentially, one by one.
This is what I tried to experiment with. `pytest` has a very nice plugin called `pytest-xdist`. It
can distribute tests among some number of workers. Ok, let's try it:

```sh
$ pip install pytest-xdist
$ pytest -v -n 8
```

It just started to execute the tests in parallel! But in my setup all tests were executed against
one container. That caused undesirable side effects and may tests failed. So we need to give a
dedicated container to each worker. For that I added a fixture that spawns a container on some local
host address and then python selenium uses it to interact with a browser. Here is the fixture:

```python
@pytest.fixture(scope="session")
def selenium_host(worker_id):
    oktet = 1 if worker_id == "master" else int(worker_id.lstrip("gw")) + 1
    host = f"127.0.0.{oktet}"
    ps = subprocess.run(
        [
            "sudo",
            "podman",
            "run",
            "--rm",
            "-d",
            "-p",
            f"{host}:4444:4444",
            "--shm-size=2g",
            "quay.io/redhatqe/selenium-standalone",
        ],
        stdout=subprocess.PIPE,
    )
    yield host
    container_id = ps.stdout.decode("utf-8").strip()
    subprocess.run(["sudo", "podman", "kill", container_id])
```

As you can see I just get a worker id and make a host address from it. I use `podman` to manage
containers. Unfortunately, version 2.0.2 has a nasty [bug](https://github.com/containers/podman/issues/7016)
that breaks networking in rootless containers. So I had to run containers with `sudo` but I'll
remove it when the bug will be fixed. Local experiments went fine. The next task is to prepare the
CI system. As I told earlier I was using Travis CI and it has one drawback. It doesn't have `podman`
preinstalled. Strictly speaking nothing could prevent me to use `docker` but I prefer `podman` due
to its daemonless approach and rootless containers.

In the end I switched to Github Actions. Their instances have `podman` preinstalled and Actions have
a nice feature of shared steps. But in other aspects I wouldn't highlight that CI system among
others. Here is an excerpt of `workflow.yaml`:

```yaml
...
test:
  runs-on: ubuntu-latest
  needs: lint
  strategy:
    matrix:
      browser: ["firefox", "chrome"]
  steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
    - name: Install dependencies
      run: |
        pip install -U setuptools pip
        pip install pytest pytest-cov codecov pytest-xdist
        python setup.py install
    - name: Test with pytest
      env:
        BROWSER: ${{ matrix.browser }}
      # Containers are spawn from the tests now.
      # "-n 5" means that 5 workers are used with 5 dedicated containers.
      # "--dist=loadscope" means tests spread among workers by modules. Each worker executes tests
      # from the same module.
      run: |
        pytest -v -n 5 --dist=loadscope --no-cov-on-fail --cov=widgetastic_patternfly4 --cov-report=xml:/tmp/coverage.xml
    - name: Publish coverage
      uses: codecov/codecov-action@v1
      with:
        file: /tmp/coverage.xml
...
```

So what about time execution? It's reduced to **11** minutes and it's two times faster! Not bad. Can
I do better?

## References

* [widgetastic.patternfly4](https://github.com/RedHatQE/widgetastic.patternfly4)
* [pytest-xdist](https://github.com/pytest-dev/pytest-xdist)
* [Patternfly](https://www.patternfly.org/v4/documentation/react/overview/release-notes)
* [webdriverdownloader](https://github.com/leonidessaguisagjr/webdriverdownloader)
* [podman](https://podman.io)
* [selenium-standalone](https://github.com/RedHatQE/selenium-images)
