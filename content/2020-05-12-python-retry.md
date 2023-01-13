---
title: Python retry!
tags: python
---
In programming it's quite often you need to wait for an action to complete or some service
availability. There are many ways and tools which able to do that. I would like to tell about two
python libraries I've worked with.

## [wait_for](https://github.com/RedHatQE/wait_for)

It's a small library originally created by my colleague Pete Savage
[@psav](https://github.com/psav). `wait_for` is heavily used in web UI tests. When you click some
button you not always get the result immediately. Request processing can take some time. Some
application will show the result after page refresh, more modern applications use XHR and tons of
scripts 🤑 to update the page. In both cases you cannot just perform button clicking in the python
code. You have to wait until the result appears and only after that continue execution. Let me
provide some examples of usage:

```python
view.submit_button.click()
wait_for(
    lambda: view.flash.is_displayed,
    delay=10,
    timeout=120
)
view.flash.assert_no_error()
```

Here test automation clicks a button and then wait for another element appearing in the UI.
`wait_for` just executes `lambda: view.flash.is_displayed` over and over again until result will be
`True` or time out.

`wait_for` has a nice decorator:

```python
@wait_for_decorator(delay=10, timeout=300)
def volume_type_is_displayed():
    volume_type.refresh()
    return volume_type.exists
```

## [tenacity](https://github.com/jd/tenacity)

Everything gets a lot more fun when you start to use `asyncio`. First of all you'll find out that
`time.sleep()` blocks the main thread and you cannot use it in your asynchronous code. But wait
`wait_for` uses `time.sleep()`
[underneath](https://github.com/RedHatQE/wait_for/blob/master/wait_for/__init__.py#L192). I wanted
to add `asyncio` support but before I started I decided to search if someone already did it (yeah
I'm lazy I know). This is how I discovered `tenacity` (credits to
[Julien Danjou](https://julien.danjou.info/)). You can use it in both synchronous and
asynchronous code under the same API. My task was to upload a payload to a server and wait for the
result from some REST API endpoint. But I wanted to upload a lot of payloads and check the results
after that. `tenacity` and `asyncio` fit perfectly for that task. Here is an example:

```python
import asyncio
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import retry_if_result
from tenacity import stop_after_delay
from tenacity import wait_fixed

@retry(
    stop=stop_after_delay(300),
    wait=wait_fixed(4),
    retry_error_callback=lambda retry_state: False,
    retry=(retry_if_result(lambda value: value is False) | retry_if_exception_type(Exception)),
)
async def find_host(session, hostname):
    url = f"https://example.com/hostnames/{hostname}"
    resp = await session.get(url)
    if resp.status != 200
        return False
    resp_json = await resp.json()
    return bool(resp_json["data"])

async def upload_payload(session, hostname):
    data = f"some_payload_with_{hostname}"
    resp = await session.post("https://example.com", data=data)
    is_host_found = await find_host(session, hostname)
    message = "host %s was found!" if is_host_found else "host %s wasn't found in time"
    logger.info(message, hostname)

async def scheduler(session, base_hostname, num_uploads):
    tasks = []
    for i in range(num_uploads):
        hostname = f"{i}.{base_hostname}"
        task = upload_payload(session, hostname)
        task = asyncio.ensure_future(task)
        tasks.append(task)
    await asyncio.wait(tasks)
    await session.close()
```

What's happening in this piece of code?

1. `scheduler` creates number of tasks `upload_payload` equals to `num_uploads`.
2. `upload_payload` uploads a payload ans waits for the result in `find_host`
3. `find_host` every 4 seconds checks `f"https://example.com/hostnames/{hostname}"` endpoint and
returns `True` if it's found. Otherwise it fails with timeout after 5 minutes.

## Conclusion

`tenacity` is a powerful library and if you need to retry operations in asynchronous code it's the
best choice. In other cases `wait_for` will be more than enough. In my opinion it has simpler
API and doesn't force you to decorate functions.
