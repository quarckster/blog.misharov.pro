---
layout: post
title: Selenium please wait!
tags: [selenium, javascript, testing]
---
When you test your web application with Selenium there is a one fundamental problem. Due to dynamic
nature of modern web pages you cannot interact with elements on the web page immediately after
loading. What can we do with that?

## Details of the problem

In old good times when javascript was used mostly for showing snowflakes Selenium was a perfect
solution for testing web UIs. Web pages were mostly static. When a web page was loaded by a browser
we could start interact with it via our automation suite. What do we have now? Modern frontends are
complex applications and the loaded web page doesn't mean that it's ready for automation. We should
wait until it be ready. But how long and what exactly should we wait for? I would highlight three
factors that can interfere in Selenium automation:

1. Animation
2. Rendering
3. XHR requests

## Animation

As I wrote before we expect a static web page without any moving parts in order to successfully use
our Selenium based automation. Various animations might break it. For example a dropdown might
expand its content not immediately but after animation time. What we can do about it? Usually such
components designate their state via `class` html attribute. You can look how it's implemented in
[Twitter Bootstrap Accordion](https://getbootstrap.com/docs/4.5/components/collapse/#accordion-example).
Div tag of the collapsed group item has `collapse` in class attribute:

```html
<div id="collapseOne"
     class="collapse"
     aria-labelledby="headingOne"
     data-parent="#accordionExample"
     style="">
</div>
```

During the animation it's changed to `collapsing`:

```html
<div id="collapseOne"
     class="collapsing"
     aria-labelledby="headingOne"
     data-parent="#accordionExample"
     style="">
</div>
```

And expanded state has `collapse show` value.

This fact gives us ability to know exact time when we can work with the component. We could use one
libraries from [Python retry!]({% post_url 2020-05-12-python-retry %}) in order to periodically
fetch value of `class` attribute. This method is not ideal. First of all, this method requires an
individual approach for every component that has the animation. Secondly, not all components change
their attributes during the animation.

## Rendering

It's a quite new problem which I faced working with React based UI. A component is not shown
right after [XHR](#xhr) because javascript code needs some time to render the HTML. There is no easy
solution except periodically polling the web page to define if the component is displayed or not:

```python
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from wait_for import wait_for_decorator

driver = webdriver.Firefox()
driver.get("http://some_url")

@wait_for_decorator(delay=5, timeout=60)
def find_element():
     try:
          element = driver.find_element_by_xpath(".//div")
     except NoSuchElementException:
          return False
     return element.is_displayed()
```

## XHR

I don't want to dive into [details](https://en.wikipedia.org/wiki/XMLHttpRequest) of this API the
only thing is important to us as testers that javascript uses it to modify a web page without
reloading. It causes serious problems because Selenium doesn't provide any method for your
automation that would allow you to know when XHR is started and finished. There are some indirect
ways to do that. You can look up an element on the web page until it will appear. It's a quite slow
method and it's not error prone. Some libraries provide an API for XHR. For instance when jQuery
executions are completed, you will have the initial `jQuery.active == 0`. But what if our UI doesn't
use jQuery but React or Angular?

We can fundamentally solve this problem by changing the frontend code. The idea is to intercept all
XHR requests and track their states in some variable which we can read in Selenium. We made this in
[cloud.redhat.com](https://github.com/RedHatInsights/insights-chrome/blob/master/src/js/iqeEnablement.js):

```javascript
let xhrResults = [];
let fetchResults = {};
let initted = false;
let wafkey = null;

function init () {
    console.log('[iqe] initialized');

    // Here we substitute original XHR methods and also "fetch"
    const open = window.XMLHttpRequest.prototype.open;
    const send = window.XMLHttpRequest.prototype.send;
    const oldFetch = window.fetch;

    // must use function here because arrows dont "this" like functions
    window.XMLHttpRequest.prototype.open = function openReplacement(_method, url) {
        this._url = url;
        const req = open.apply(this, arguments);
        if (wafkey) {
            this.setRequestHeader(wafkey, 1);
        }

        return req;
    };

    // must use function here because arrows dont "this" like functions
    window.XMLHttpRequest.prototype.send = function sendReplacement() {
        // Here we put the request object into a xhrResults array where we can track the states of
        // all requests
        xhrResults.push(this);
        return send.apply(this, arguments);
    };

    // Interception for "fetch" is different but the idea is the same
    window.fetch = function fetchReplacement(path, options, ...rest) {
        let tid = Math.random().toString(36);
        let prom = oldFetch.apply(this, [path, {
            ...options || {},
            headers: {
                ...(options && options.headers) || {},
                [wafkey]: 1
            }
        }, ...rest]);
        fetchResults[tid] = arguments[0];
        prom.then(function () {
            delete fetchResults[tid];
        }).catch(function (err) {
            delete fetchResults[tid];
            throw err;
        });
        return prom;
    };
}

export default {
    // We don't want to enable XHR interception in production so we should do it explicitly via
    // some mechanism. We chose a localStorage variable.
    init: () => {
        if (!initted) {
            initted = true;
            if (window.localStorage &&
                window.localStorage.getItem('iqe:chrome:init') === 'true') {
                wafkey = window.localStorage.getItem('iqe:wafkey');
                init();
            }
        }
    },
    // These variables we can read in Selenium using execute_script() method
    hasPendingAjax: () => {
        const xhrRemoved = xhrResults.filter(result => result.readyState === 4 || result.readyState === 0);
        xhrResults = xhrResults.filter(result => result.readyState !== 4 && result.readyState !== 0);
        xhrRemoved.map(e => console.log(`[iqe] xhr complete:   ${e._url}`));
        xhrResults.map(e => console.log(`[iqe] xhr incomplete: ${e._url}`));
        Object.values(fetchResults).map(e => console.log(`[iqe] fetch incomplete: ${e}`));
        return xhrResults.length > 0 || fetchResults.length > 0;
    },
    isPageSafe: () => !document.querySelectorAll('[data-ouia-safe=false]').length !== 0,
    xhrResults: () => {
        return xhrResults;
    },
    fetchResults: () => {
        return fetchResults;
    }

};
```

As you can see it's quite small piece of code and it allows us to know states of all XHR very
precisely. Moreover we don't depend on any framework because we overrode the primitives that are
used by all frameworks.

So what do we have in the end? It is possible to trace all javascript "activities" though it's a
quite complex task. We can trace animation and rendering via some indirect ways such as polling web
elements attributes. XHR requests tracing requires changing frontend code but it gives us the best
results. This gave us the idea that we could continue changing the frontend code to make developing
automation suite a bit easier and less hacky. My colleagues [Pete Savage](https://github.com/psav),
[Ronny Pfannschmidt](https://github.com/RonnyPfannschmidt) and [Karel Hala](https://github.com/karelhala)
created a specification for frontend developers that helps to solve aforementioned problems. The
specification is named [Open UI Automation](https://ouia.readthedocs.io). In the next post I'll
explain why it's cool and how it can help both frontend developers and testers.
