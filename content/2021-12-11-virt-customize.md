---
title: Virtual machine image customization
tags: vm, virt-customize, libguestfs
---

I work with Linux containers and container images everyday. I often create new images using `podman`
or `buildah`. One day I needed to build a custom image of a virtual machine and in this post you'll
read how I did it.

## Prerequisite

In the post [GitLab custom executor for Openstack]({filename}2021-06-18-gitlab-openstack-executor.md)
I explained how to create a GitLab executor for Openstack. That executor provisions an Openstack
instance for each job and run a job script in it. There is some required software to run jobs:

> The user must set up the environment, including the following that must be present in the `PATH`:
>
>    Git: Used to clone the repositories.
>
>    Git LFS: Pulls any LFS objects that might be in the repository.
>
>    GitLab Runner: Used to download/update artifacts and cache. 

It means that we need to customize an instance image to include prerequisites.

## libguestfs

After some research I found a tool that does exactly what I need. `libguestfs` project provides
a set of utilities for accessing and modifying virtual machine disk images. `virt-customize` can
customize disk images in place. I chose Fedora Cloud image as environment for running GitLab jobs.
The commands to add required software are very simple:

1. Install `libguestfs`
2. Download or build `gitlab-runner`
3. Create a file with a `virt-customize` scenario:

    ```sh
    cat > commands.txt <<EOF
    install git-core,git-lfs
    copy-in <path to gitlab-runner binary>:/usr/bin/
    chmod 0755:/usr/bin/gitlab-runner
    selinux-relabel
    EOF
    ```

4. Run `virt-customize`:

    ```sh
    virt-customize -v -a Fedora-Cloud-Base-35-1.2.x86_64.qcow2 --commands-from-file commands.txt
    ```

Pay attention to the `selinux-relabel` customization option. This is required for VMs that supports
SELinux. Fedora instance cannot properly start if you modified the image without relabelling.

References:

* <https://libguestfs.org/virt-customize.1.html>
* <https://docs.gitlab.com/runner/executors/custom.html#prerequisite-software-for-running-a-job>
* <https://alt.fedoraproject.org/cloud/>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/23)
