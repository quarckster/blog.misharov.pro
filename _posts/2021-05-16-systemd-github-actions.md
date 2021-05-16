---
layout: post
title: How to run a rootless podman service in Github Actions
tags: [systemd, ci]
---
Managing user services by `systemd` in Github Actions runners is not so obvious as in your local
machine. Here is what I found when I was trying to start rootless podman as a service.

## Podman socket

I was playing with `podman-py` package and for that I needed to start a podman socket. Systems with
`systemd` use `systemctl` utility to manage services, sockets, timers and other objects. Systemd can
connect to the user service manager and this is important if you run podman in the rootless mode.
Thus you need this command to start podman service and make it listen to a socket:

```sh
systemctl --user enable --now podman.socket
systemctl --user status podman.socket   
● podman.socket - Podman API Socket
     Loaded: loaded (/usr/lib/systemd/user/podman.socket; enabled; vendor preset: enabled)
     Active: active (listening) since Sat 2021-05-15 15:17:54 CEST; 1h 10min ago
   Triggers: ● podman.service
       Docs: man:podman-system-service(1)
     Listen: /run/user/1000/podman/podman.sock (Stream)
     CGroup: /user.slice/user-1000.slice/user@1000.service/podman.socket

May 15 15:17:54 thinkpad-t480s systemd[959]: Listening on Podman API Socket
```

After that you can use podman REST API and `podman-py`.

## Github Actions runner

Although this command perfectly works on a regular system in Github Actions I got the error:

```text
Failed to connect to bus: No such file or directory
```

After some googling I found that the reason is `/lib/systemd/systemd --user` process doesn't run in
a runner. This process is responsible for managing user services. In order to enable it you have to
enable lingering for a user you logged in:

```sh
loginctl enable-linger $(whoami)
```

But this is not enough. Rootless podman puts its socket to this path
`$XDG_RUNTIME_DIR/podman/podman.sock` and Github Actions environment doesn't have `$XDG_RUNTIME_DIR`
variable set. Let's set it in this way:

```sh
export XDG_RUNTIME_DIR=/run/user/$UID
```

or you can add it to Github Actions environment like this:

```yaml
- name: Set XDG_RUNTIME_DIR
  run: echo "XDG_RUNTIME_DIR=/run/user/$UID" >> $GITHUB_ENV
```

And there is one more problem. [@eriksjolund](https://github.com/eriksjolund) found that
`loginctl enable-linger` needs some time to finish and `sleep 1` is needed after.

## Podman service

Despite on I was able to enable podman socket using systemd facilities the implementation looks a
bit hacky. Fortunately, `podman` can create a listening service that will answer API calls. I used
this command to start the service in the background that listens to API calls in
`${XDG_RUNTIME_DIR}/podman/podman.sock`:

```sh
podman system service --time=0 unix://${XDG_RUNTIME_DIR}/podman/podman.sock &
```

References:

* <https://superuser.com/questions/1561076/systemctl-use-failed-to-connect-to-bus-no-such-file-or-directory-debian-9>
* <https://github.com/eriksjolund/user-systemd-service-actions-workflow/>
* <https://lists.podman.io/archives/list/podman@lists.podman.io/thread/E2PHNHZ6QVWMOT4Y7PVRIPDY7SVFTWG2/?sort=thread>
* <http://docs.podman.io/en/latest/markdown/podman-system-service.1.html>
* <https://www.freedesktop.org/software/systemd/man/loginctl.html>
* <https://github.com/containers/podman-py>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/14)
