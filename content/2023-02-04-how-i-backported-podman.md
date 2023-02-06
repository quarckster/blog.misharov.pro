---
title: How I backported Podman 4 to Ubuntu 22.04
tags: packaging, ppa, podman, ubuntu, debian
---

I love containers, it's really cool technology to preserve and distribute environments. To manage
containers I prefer `podman` and its friends `buildah` and `skopeo`. `podman` 4 introduced many cool
features but it's unavailable in Ubuntu 22.04 which is my primary OS, the latest version there is
3.4.4. Thus, I decided to backport `podman` from Debian Testing where it's already packaged by
mighty Debian maintainers.

## Workflow

As you might know Canonical drives Launchpad. This is a large portal that combines plenty of tools
around Ubuntu. One of these tools is PPA or Personal Package Archive. It allows you to build and
distribute your custom `deb` packages. I used many PPAs in the past but never created my own.
Moreover, I've never tried to build a `deb` package. There was a lot of fun ahead :)

To build `deb` packages Launchpad accepts so-called source packages as input. Fortunately, I didn't
have to make them from the scratch thanks to the great job of Debian maintainers. Thus, the
backporting process looked as follows:

1. Get sources from Debian testing.
2. Update the changelog.
3. Rebuild the source package in Ubuntu 22.04.
4. Upload the resulting artifacts to my PPA.
5. Profit!

## Fun

First of all, it was hard to get the right documentation about package building in Debian. Don't get
me wrong, there is documentation but it's all over the place, it's duplicated and out of date
sometimes. Here are some links I found on `debian.org`:

* <https://wiki.debian.org/BuildingAPackage>
* <https://wiki.debian.org/Packaging>
* <https://wiki.debian.org/Packaging/Intro>
* <https://wiki.debian.org/HowToPackageForDebian>
* <https://wiki.debian.org/BuildingTutorial>
* <https://www.debian.org/doc/manuals/maint-guide/build.en.html>

After reading I got the understanding of what tools I should use and what commands need to be run.

### Tooling

All package manipulations I did in the containers. I ran both `docker.io/library/ubuntu:22.04` and
`docker.io/library/debian:bookworm` with one shared volume:

```sh
podman run -it --rm -v $(pwd):/mnt docker.io/library/debian:bookworm bash
podman run -it --rm -v $(pwd):/mnt docker.io/library/ubuntu:22.04 bash
```

To build packages you need to install two packages: `devscripts` and `build-essential`. In the
Debian container `devscripts` will be enough. Don't forget to add source repositories into
`/etc/apt/sources.list` and update packages index:

```sh
echo "deb-src http://debian.org/debian testing main" >> /etc/apt/sources.list
apt-get update
apt-get install -y devscripts
```

### Sources

To get the sources you should run only one command in the Debian container:

```sh
apt-get source podman
```

There will be downloaded three files:

* libpod_4.3.1+ds1-5.dsc - package metadata
* libpod_4.3.1+ds1-5.debian.tar.xz - an archive with building recipes, patches, package changelog
  and other stuff
* libpod_4.3.1+ds1.orig.tar.xz - source code

`dpkg-source` script from `devscripts` extracts archives applies patches and you will get a source
code directory with the `debian` directory within. Basically, that's the only action we should do in
the Debian container. The following operations I made in the Ubuntu container.

### Change log

Before uploading sources to Launchpad a new entry in the `changelog` file should be added. It can be
done with any text editor but there is a dedicated utility `dch` that adds a time stamp and bumps
version. You just need to write what has been changed. I didn't change anything so I put only this
line:

```text
upload to ppa:quarckster/containers
```

### Building

Here starts the __fun__. Launchpad accepts only source packages and to produce such you should run
`dpkg-buildpackage` from `devscripts`:

```sh
dpkg-buildpackage -us -uc -sa -S
```

The command will fail due to missing __build__ dependencies. I decided to ignore them and added
`-d` flag. After that I got four new files:

* libpod_4.3.1+ds1-5.1ubuntu1ppa1.debian.tar.xz
* libpod_4.3.1+ds1-5.1ubuntu1ppa1.dsc
* libpod_4.3.1+ds1-5.1ubuntu1ppa1_source.buildinfo
* libpod_4.3.1+ds1-5.1ubuntu1ppa1_source.changes

### Uploading to Launchpad

Debian and Ubuntu provide utility named `dput` to upload source packages. All you need to do is just
to specify a path to `.changes` files and the PPA name:

```sh
dput ppa:quarckster/containers libpod_4.3.1+ds1-5.1ubuntu1ppa1_source.changes
```

After that, all required files will be uploaded. But before you must sign `.changes` with your gpg
key:

```sh
debsign -k "<key id>" libpod_4.3.1+ds1-5.1ubuntu1ppa1_source.changes
```

Actually, it can be done during the building but I didn't want to configure gpg in the container.

### Dependencies

Do you remember I ignored build dependencies when I built the source package? Of course, my build
failed and I had to repack and upload the whole dependencies graph. Maybe there is a smart way to do
that but I didn't figure out anything better than waiting until a build fails, then check the logs,
finding missing dependencies and doing a new packaging iteration. I had to upload 38 packages in
total.

### Profit

Now I have modern version of `podman` on my operating system. Feel free to use it as well.

<https://launchpad.net/~quarckster/+archive/ubuntu/containers>

## Even more fun

I felt a superpower and decided to backport a new networking backend for `podman`. It consists of
two packages `netavark` and `aardvark-dns`. I didn't realize how deep this rabbit hole. `podman` is
missing only 38 packages because most other dependencies from this graph are available in Ubuntu
22.04:

![Podman dependency graph]({static}/assets/img/2023-02-06-podman_resized.png)

<center>Fig. 1 - Podman dependency graph (<a href="/assets/img/2023-02-06-podman.png">high resolution</a>)</center>

On the other hand, `netavark` and `aardvark-dns` are completely new packages and all build
dependencies exist only in Debian Testing:

![Netavark dependency graph]({static}/assets/img/2023-02-06-netavark_resized.png)

<center>Fig. 2 - Netavark dependency graph (<a href="/assets/img/2023-02-06-netavark.png">high resolution</a>)</center>

When I uploaded around one hundred packages to my PPA I encountered circular dependency and further
backporting stuck.

### Vendoring

Rust package manager `cargo` has ability to download all dependencies and configure the compiler
to use this local cache for building. You just need two commands:

```sh
cargo vendor > .cargo/config.toml
cargo generate-lockfile
```

New files should be included into `orig.tar.xz` archive and after that the package was successfully
built.

## Conclusion

Packaging is fun :) I want to give credits to Debian maintainers because they do a great job. All I
need to do is just to change a couple of line in the `changelog` file and run some commands. The
most interesting part is located in the `rules` file which is a `Makefile`. It contains the recipe
and all logic.

> The only thing that really worried me was the `rules` file. There is nothing in the world more
> helpless and irresponsible and depraved than a man in the depths of hacking `rules` file. And I
> knew I'd get into that rotten stuff pretty soon. Probably next time.

## References

* <https://launchpad.net/~quarckster/+archive/ubuntu/containers>
* <https://help.launchpad.net/Packaging/PPA/Uploading>
* <https://podman.io>
* <https://github.com/containers/netavark>
* <https://wiki.debian.org/BuildingAPackage>
* <https://wiki.debian.org/Packaging>
* <https://wiki.debian.org/Packaging/Intro>
* <https://wiki.debian.org/HowToPackageForDebian>
* <https://wiki.debian.org/BuildingTutorial>
* <https://www.debian.org/doc/manuals/maint-guide/build.en.html>
* <https://wiki.debian.org/DependencyHell>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/28)
