---
title: install_requires vs requirements.txt
tags: python, pip
---
When I started working at Red Hat my first job was contribution to integration tests of one web
application. The tests are written Python and the repository has both `setup.py` and
`requirements.txt`. But why?

## requirements.txt

Python and many other interpreted languages such as Ruby and JS require a prepared environment to
run some code. This environment should have all dependencies installed with correct versions. In
Python we use `requirements.txt` file for describing such environment. It's just a text file with
package names and versions. e.g.:

```txt
pytest==6.2.2
django==3.1.5
```

Then using `pip` we can recreate this environment in any other place. It makes a lot of sense when
we deploy a Python application.

## install_requires

But what about dependencies of dependencies? Python code is distributed via *packages*. A Python
package is a directory that follows a certain file structure and has `setup.py` file that is a
build script for `setuptools`. If your package uses other packages you can specify them in
`install_requires` argument:

```python
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="example-pkg-YOUR-USERNAME-HERE", # Replace with your own username
    version="0.0.1",
    author="Example Author",
    author_email="author@example.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
    install_requires=["pytest>6.0.0", "django"]
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
```

## Applications vs packages

So we now know packages need only `install_requires` in `setup.py` in order to specify dependencies.
Application and standalone scripts need only `requirements.txt` for reproducing an environment.
Things get more complicated when your package is an application as well. `setuptools` can generate
a python script that can be placed in `$PATH`. It can call some entry point function in your
package. During the deployment we would like to have a reproducible environment and as I told
before `requirements.txt` is what we need to use to recreate such environments.

### pytest

Let me consider the case that I started the post with. `pytest` is the best choice for developing
tests on any level: unit, functional and integration. The integration tests I worked on are really
huge. In order to manage the complexity we created some abstractions to interact with the web
application we want to test. These abstractions are organized as a package. In the tests we import
that package and in fact we test its code. Let me provide a simplified directory structure:

```txt
mypkg/
    __init__.py
    app.py
    view.py
tests/
    test_app.py
    test_view.py
setup.py
requirements.txt
```

Interesting thing here is that our tests is the application :) And for deploying our application
in CI we need to recreate the environment and that's why we have both `setup.py` and
`requirements.txt` in one repository. Of course nothing prevents you to divide the tests and the
package in different repositories but I think it would be inconvenient. 

## References

* <https://packaging.python.org/discussions/install-requires-vs-requirements/>
* <https://caremad.io/2013/07/setup-vs-requirement/>
* <https://github.com/ManageIQ/integration_tests/>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/7)
