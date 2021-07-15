---
layout: post
title: GitLab custom executor for Openstack
tags: [openstack, gitlab-runner, gitlab ci]
---

Gitlab CI doesn't have built-in support of Openstack but provides the API to add such support via
`Drivers`. In this post I'll demonstrate how to create such drivers.

## Preamble

I've already written about Gitlab CI here. In particular in
[Gitlab runner in Openshift]({% link _posts/2020-05-08-gitlab-runner-in-openshift.md %}). I shared my
experience with using Gitlab CI and Kubernetes executor. In some cases, containers don't fit your
workflows and you would like to run Gitlab CI jobs on real VMs. Gitlab CI provides various executors
including `shell`, `ssh`, `parallels` and `virtualbox` that use virtual machines as an environment
for job execution. The problem with `shell` and `ssh` executors that they don't provide a clean
environment. There might be undesired side-effects and leftovers from prior jobs. As for `parallels`
and `virtualbox` executors they look exotic and a bit outdated solutions. They're just not scalable.
It would much better to leverage the power of one of the cloud providers to provision VMs for our
Gitlab CI jobs.

## Openstack

OpenStack is a free, open standard cloud computing platform. It has REST API to manage instances and
that's exactly what we need for our driver. Moreover, Openstack project provides CLI utility and
Python SDK. We will use it for creating an Openstack driver for Gitlab CI.

```shell
pip install openstacksdk
```

## Custom executor

According the documentation to set up a custom executor for `gitlab-runner` we should provide the
following config:

```toml
[[runners]]
 name = "custom"
 url = "https://gitlab.com"
 token = "TOKEN"
 executor = "custom"
 builds_dir = "/builds"
 cache_dir = "/cache"
 [runners.custom]
   config_exec = "/path/to/config_executable" # optional
   config_args = [ "SomeArg" ] # optional
   config_exec_timeout = 200 # optional

   prepare_exec = "/path/to/prepare_executable"
   prepare_args = [ "SomeArg" ] # optional
   prepare_exec_timeout = 200 # optional

   run_exec = "/path/to/run_executable"
   run_args = [ "SomeArg" ] # optional

   cleanup_exec = "/path/to/cleanup_executable"
   cleanup_args = [ "SomeArg" ] # optional
   cleanup_exec_timeout = 200 # optional

   graceful_kill_timeout = 200 # optional
   force_kill_timeout = 200 # optional
```

As you can see each Gitlab CI job contains four stages: `config`, `prepare`, `run` and `cleanup`.
Our task is to create scripts for corresponding stages.

## Config

It's not a mandatory stage but it's nice to have. An executable in this stage should print to stdout
a JSON string with specific keys. In my case the executable is a simple shell script:

```bash
#!/usr/bin/env bash

cat << EOS
{
 "driver": {
   "name": "Openstack",
   "version": "0.0.1"
 }
}
EOS
```

After adding this to `config_exec` job logs are started from these lines:

```text
Running with gitlab-runner 13.12.0 (7a6612da)
 on openstack hkLsofs5
Preparing the "custom" executor
Using Custom executor with driver Openstack 0.0.1...
```

## Prepare

Here we need to provision a VM where the job scripts will be executed. We will use python and
`openstacksdk` package. Besides we will need `paramiko` package. It's a well-known python
implementation of SSH for both the server and the client. We use `paramiko` in this stage to check
if the VM is ready to accept commands via SSH. Here is the script I've created:

```python
#!/usr/bin/env python
import sys
import traceback

import openstack
import paramiko

# a module that contains required parameters to set up VMs and an SSH connection.
import env

def provision_server(conn: openstack.connection.Connection) -> openstack.compute.v2.server.Server:
   image = conn.compute.find_image(env.BUILDER_IMAGE)
   flavor = conn.compute.find_flavor(env.FLAVOR)
   network = conn.network.find_network(env.NETWORK)
   server = conn.compute.create_server(
       name=env.VM_NAME,
       flavor_id=flavor.id,
       image_id=image.id,
       key_name=env.KEY_PAIR_NAME,
       security_groups=[{"name": env.SECURITY_GROUP}],
       networks=[{"uuid": network.id}],
   )
   return conn.compute.wait_for_server(server, wait=600)


def get_server_ip(
   conn: openstack.connection.Connection, server: openstack.compute.v2.server.Server
) -> str:
   return list(conn.compute.server_ips(server))[0].address


def check_ssh(ip: str) -> None:
   ssh_client = paramiko.client.SSHClient()
   # RSASHA256Key is not a part of mainline paramiko. I took it from this PR
   # https://github.com/paramiko/paramiko/pull/1643.
   pkey = paramiko.rsakey.RSASHA256Key.from_private_key_file(env.PRIVATE_KEY_PATH)
   ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
   ssh_client.connect(
       hostname=ip,
       username=env.USERNAME,
       pkey=pkey,
       look_for_keys=False,
       allow_agent=False,
       timeout=60,
   )
   ssh_client.close()


def main() -> None:
   print("Connecting to Openstack", flush=True)
   try:
       conn = openstack.connect()
       print(f"Provisioning an instance {env.VM_NAME}", flush=True)
       server = provision_server(conn)
       ip = get_server_ip(conn, server)
       print(f"Instance {env.VM_NAME} is running on address {ip}", flush=True)
       conn.close()
       print("Checking SSH connection", flush=True)
       check_ssh(ip)
       print("SSH connection has been established", flush=True)
   except Exception:
       traceback.print_exc()
       # gitlab-runner expects a certain exit code in case of failure.
       sys.exit(int(env.SYSTEM_FAILURE_EXIT_CODE))


if __name__ == "__main__":
   main()
```

I believe it's really straightforward and it's clear what the script does. But there are a couple of
moments I'd like to highlight.

### Paramiko and RSA keys

When I was playing with `paramiko` to test how it works with VMs SSH I got `Authentication error`
exception. It was very confusing because the OpenSSH client connected without any issue with the
same private key. I even generated a key using `paramiko` and then tried to authenticate but no
luck. I found out that `paramiko` doesn't support modern RSA algorithms. There is a
[PR](https://github.com/paramiko/paramiko/pull/1643) that adds this functionality and I had to build
and install `paramiko` from it in order to get it working.

```shell
pip install -U git+https://github.com/kkovaacs/paramiko.git@rsa-sha2-algorithms
```

### print() flush

During the testing, I noticed that job logs are displayed in Gitlab UI not immediately but only
when the script finished. That was the strange and undesired effect. The issue was in the default
behavior of the python `print()` function. For sake of performance reasons stdout in python is
buffered. The output will be emitted only when the buffer is filled. In order to forcibly _flush_
the buffer `print()` has boolean `flush` parameter. When I set `flush=True` in all `print()` calls
job logs in Gitlab UI got live streaming.

## Run

A VM is provisioned and we can connect to it via SSH. Now we can execute some commands and scripts.
`gitlab-runner` generates shell scripts from job definitions then it dumps them to the file system
and passes a path as an argument to our `run` executable. Our `run.py` should read that script and
send its content directly to the stdin of some shell interpreter. In my case it's `/bin/bash`. Here
is the content of `run.py`:

```python
#!/usr/bin/env python
import sys

import openstack
import paramiko

import env


def get_server_ip(conn: openstack.connection.Connection) -> str:
   server = list(conn.compute.servers(name=env.VM_NAME, status="ACTIVE"))[0]
   return list(conn.compute.server_ips(server))[0].address


def execute_script_on_server(ssh: paramiko.client.SSHClient, script_path: str) -> int:
   # paramiko's exec_command() returns a tuple of stdin, stdout, stderr
   # file-like objects
   stdin, stdout, stderr = ssh.exec_command("/bin/bash")
   # Read the script content and send it to the remote bash stdin.
   # We emulate this shell command:
   # ssh user@host /bin/bash < script.sh
   with open(script_path) as f:
       stdin.channel.send(f.read())
       stdin.channel.shutdown_write()
   # Here we read the output line by line but only first 2048 bytes. It
   # prevents possible overflows if a line is huge.
   for line in iter(lambda: stdout.readline(2048), ""):
       # Don't forget to flush the buffer for live log streaming
       print(line, sep="", end="", flush=True)
   # When the script execution finished we save the exit code.
   exit_status = stdout.channel.recv_exit_status()
   if exit_status != 0:
       # In case of non 0 exit code print stderr as well.
       for line in iter(lambda: stderr.readline(2048), ""):
           print(line, sep="", end="", flush=True)
   return exit_status


def get_ssh_client(ip: str) -> paramiko.client.SSHClient:
   ssh_client = paramiko.client.SSHClient()
   pkey = paramiko.rsakey.RSASHA256Key.from_private_key_file(env.PRIVATE_KEY_PATH)
   ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
   ssh_client.connect(
       hostname=ip,
       username=env.USERNAME,
       pkey=pkey,
       look_for_keys=False,
       allow_agent=False,
       timeout=60,
   )
   return ssh_client


def main() -> None:
   conn = openstack.connect()
   ip = get_server_ip(conn)
   ssh_client = get_ssh_client(ip)
   # gitlab-runner passes a path to the script in the first argument. We read
   # that value in sys.argv[1]
   exit_status = execute_script_on_server(ssh_client, sys.argv[1])
   ssh_client.close()
   if exit_status != 0:
       # gitlab-runner expects a certain exit code in case of a build failure.
       sys.exit(int(env.BUILD_FAILURE_EXIT_CODE))


if __name__ == "__main__":
   main()
```

## Clean up

Let me quote the official docs:

> This final stage is executed even if one of the previous stages failed.
> The main goal for this stage is to clean up any of the environments that might
> have been set up. For example, turning off VMs or deleting containers.

`cleanup.py` is simple:

```python
#!/usr/bin/env python
import openstack

import env


def main() -> None:
   conn = openstack.connect()
   # During the prepare stage several VMs with the same name might be created.
   # Delete them all.
   for server in conn.compute.servers(name=env.VM_NAME):
       conn.compute.delete_server(server)


if __name__ == "__main__":
   main()
```

## Sequence diagrams

Here are sequence diagram of the workflow:

{:refdef: style="text-align: center;"}
![diagram 1](/assets/img/2021-06-18-gitlab-openstack-executor-1.png)
{: refdef}
{:refdef: style="text-align: center;"}
*diagram 1 - sequence diagram of prepare stage*
{: refdef}

{:refdef: style="text-align: center;"}
![diagram 2](/assets/img/2021-06-18-gitlab-openstack-executor-2.png)
{: refdef}
{:refdef: style="text-align: center;"}
*diagram 2 - sequence diagram of run stage*
{: refdef}

## Distribution

I hope you got the idea of how to create your own driver for the custom executor. But
I'd like to go further. It would be also nice to pack `gitlab-runner` with our
scripts into a container image. Later it can be deployed on a VM or
a container orchestration system such as Kubernetes. I prefer to build
`gitlab-runner` from the sources and using the multistage building. Here you will
find the content of the [Containerfile](https://github.com/RedHatQE/openstack-gitlab-executor/blob/master/Containerfile).
You can pull the latest prebuilt image from `quay.io/redhatqe/openstack-gitlab-runner:latest`.

## Usage

Just pull the image and run a container with some environment variables. They
are required to set up connections to your Openstack and VM's SSH:

```shell
podman run -it \
          -e PRIVATE_KEY="$(cat <private key filename>)"
          --env-file=env.txt \
          quay.io/redhatqe/openstack-gitlab-runner:latest

cat env.txt

RUNNER_TAG_LIST=<your value>
REGISTRATION_TOKEN=<your value>
RUNNER_NAME=<your value>
CI_SERVER_URL=<your value>
RUNNER_BUILDS_DIR=<your value>
RUNNER_CACHE_DIR=<your value>
CONCURRENT=<your value>

FLAVOR=<your value>
BUILDER_IMAGE=<your value>
NETWORK=<your value>
KEY_PAIR_NAME=<your value>
SECURITY_GROUP=<your value>
USERNAME=<your value>

OS_AUTH_URL=<your value>
OS_PROJECT_NAME=<your value>
OS_USERNAME=<your value>
OS_PASSWORD=<your value>
OS_PROJECT_DOMAIN_NAME=<your value>
OS_USER_DOMAIN_NAME=<your value>
OS_REGION_NAME=<your value>
OS_IDENTITY_API_VERSION=<your value>
OS_INTERFACE=<your value>
```

The full description of the environment variables and other details you will
find in the repository <https://github.com/RedHatQE/openstack-gitlab-executor>.

References:

* <https://github.com/RedHatQE/openstack-gitlab-executor>
* <https://docs.gitlab.com/runner/executors/custom.html>
* <https://docs.openstack.org/openstacksdk/latest/>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/18)
