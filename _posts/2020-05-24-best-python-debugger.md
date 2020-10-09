---
layout: post
title: The best Python debugger
tags: [python, debug]
---
Debugging is an essential part of programming. I guess you can agree with me that it takes
significant amount of time. Using an appropriate tool can save your time and efforts.

## pdb

This is a debugger that comes with Python standard library. This is the only advantage of it. Pdb
has quite limited functionality. You can set a break point inserting:

```python
import pdb; pdb.set_trace()
```

Since Python 3.7 you can just use built-in function `breakpoint()`. There are commands that
recognized by pdb when you enter them in during debugging session.

[Documentation](https://docs.python.org/3/library/pdb.html)

## PyCharm debugger

PyCharm is very powerful tool and one of the best IDE for Python. It has a rich debugging features.
I'm not a PyCharm user and the reason why I don't use it is the requirement to "live" inside the
IDE. Yes, you can attach PyCharm debugger to remote python processes but it's not always
convenient.

[Documentation](https://www.jetbrains.com/help/pycharm/debugging-code.html)

## pudb

This is my choice. The quote from the docs:

> Its goal is to provide all the niceties of modern GUI-based debuggers in a more lightweight and
> keyboard-friendly package. PuDB allows you to debug code right where you write and test it–in a
> terminal.

A breakpoint is set the following way:

```python
import pudb; pu.db
```

If you are using Python 3.7 or newer, you can specify `PYTHONBREAKPOINT` environment variable and
built-in `breakpoint()` will call `pudb`:

```text
# Set breakpoint() in Python to call pudb
export PYTHONBREAKPOINT="pudb.set_trace"
```

It has two killer features. It's a nice pseudo graphical UI and ability to switch to a custom shell
during a debugging session. For example you can open an `ipython` shell by pressing `!`. It opens
vast opportunities for code inspecting and examining your assumptions in the exactly same conditions
where your code fails. Of course you move up and down through the stack, set new breakpoints and
execute the code line by line and other standard debugging features.

{% picture assets/img/2020-05-24-best-python-debugger-1.png --alt pudb screenshot %}

### pytest integration

Pytest is one of my main testing frameworks and it's very nice that pudb has integration with it.
There is a pytest plugin `pytest-pudb` that can stop the execution post-mortem. Let's say your test
failed and you would like to find out a reason. So just install `pytest-pudb` package and append
`--pudb` to pytest command:

```shell
pytest --pudb
```

I often use this plugin and find it very helpful.

## References

[Documentation](https://documen.tician.de/pudb/)
