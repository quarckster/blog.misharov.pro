---
layout: post
title: Home-made remote video rendering
tags: [video, rendering, melt, kdenlive, ssh]
---

Recently I started my video blog on YouTube. To shoot videos I use DJI Action 2 camcorder. It can
record videos up to 4K@60 FPS. Obviously, resulting video files are heavy for editing and rendering.
Are there solutions on Linux that help you to work with modern high definition video? The answer is
yes and here is my approach.

## Editing

To edit video I prefer `Kdenlive`. It's a powerful open-source video editing software. The UI part
is powered by KDE and QT technologies. Rendering and editing is based on `melt` framework.
`Kdenlive` has interesting feature named `proxy clips`. Even the high-end CPUs will be brought down
to the knees when you try to edit 4K video in real time. So instead of working with original files
`Kdenlive` uses files with lower quality. My camcorder records these low-res files along with
original ones. This drastically improves your editing experience. When you render your project the
original files will be used.

## Rendering

Looks like you cannot cheat physics and you have to wait for a long time until the project will be
rendered on a weak laptop CPU. But it's not true :) What if the rendering could be performed
remotely on a more powerful machine? You just need an instance on some cloud provider such as AWS,
GCP or Azure. `Kdenlive` can generate a script for `melt` command line utility. So you don't need to
install `Kdenlive` on a remote machine. And what about video files? I the beginning I decided to
upload them using `rsync` but it would take several hours for my project. I had several hundreds of
gigabytes. I started to think if it's possible **to mount** my local directory on the remote
machine. Fortunately, everything can be done with a couple of commands. You just need `ssh` and
`sshfs`. Here are commands for Ubuntu:

0. Install the ssh server.

1. Run an `sftp` server on some port on the **local** machine:

```sh
cd <PATH THAT SHOULD BE MOUNTED ON THE REMOTE MACHINE>
ncat -l -p 34567 -e /usr/lib/openssh/sftp-server &
```

2. Make a tunnel from the remote instance to the port on the local machine and run `sshfs` and
   `bash`. Make sure that pah exists on the remote host:

```sh
ssh -t -R 34568:localhost:34567 <USER@REMOTE HOST> "sshfs localhost: <LOCAL MOUNT POINT> -o directport=34568; bash"
```

After that all you need is to run `melt <PATH TO SCRIPT>`. One thing you should know that the script
contains absolute paths to the video files. So you should either edit the script or use the same
paths on both local and remote machines.

## Results

Obviously you should have the fast enough internet connection otherwise it will be the bottleneck of
the whole pipeline. I tried that trick with two Digital Ocean instances: 48 CPUs and 16 CPUs. I
noticed that the more powerful instance doesn't give you 3x boost performance. Looks like `ffmpeg`
and encoders such as `x265` don't utilize all available CPUs. Anyway, using this approach with fast
internet connection you will speed up video rendering.

References:
* <https://mltframework.org>
* <https://kdenlive.org>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/25)
