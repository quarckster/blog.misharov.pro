---
layout: post
title: Minimalistic Selenium container image
tags: [selenium, container]
---

Containers are de facto a standard way to distribute services and software. It's convenient
to have preconfigured environment that can be activated on any machine that has a container engine
such as `docker` or `podman`. UI testing with Selenium requires certain environment including
browsers, X server and a window manager. It would be nice to have all of these packed into a one
container image.

## SeleniumHQ official container image

Selenium developers offer their container images on <https://github.com/SeleniumHQ/docker-selenium>.
There are several "flavors" for different purposes and with various content. Despite these images
are almost standard for UI testing I find them a bit bloated. If you run the following command:

```sh
podman run -it --rm selenium/standalone-firefox:latest dpkg -l
```

you will see such packages as `systemd` and `dbus` that are installed by a package manager but they
are not required for running Selenium, X server, and browsers. Moreover, these images were not
optimized to run in Openshift clusters where containers are executed under an arbitrary user id by
the moment we started to perform UI tests there. Therefore, we at Red Hat QE maintain our Selenium
container image.

## Red Hat QE Selenium container image

### Defining prerequisites

First of all, we based our container image on Fedora and second we install both Firefox and Google
Chrome. Originally, package dependencies were fully resolved by `dnf` package manager. It behaves
the same as it was on the usual desktop and installs a lot of packages that are not needed for UI
testing. I wanted to try to find the minimal set of rpm packages for the main components of the UI
testing with Selenium, Firefox, and Google Chrome browsers. We run our tests in headful mode and for
that, we need X server. To manage a browser window a window manager is required. `fluxbox` is a good
choice and I agree with Selenium developers on that. To inspect what is going on during the testing
session we can use a VNC server. Here enters `tigervnc`. It has a killer feature - `Xvnc` server:

> It is based on a standard X server, but it has a "virtual" screen rather than a physical one. X
> applications display themselves on it as if it were a normal X display, but they can only be
> accessed via a VNC viewer.

Thus, `tigervnc` provides both X and VNC servers. The final list of the prerequisites in the
installation order:

* X and VNC servers
* Window manager
* Browsers
* Web drivers
* Selenium standalone server

### Finding the minimal set of packages

I spent an evening doing some manual operations to find only the required packages for software from
our prerequisites list. The algorithm is simple:

1. Start a container:

   ```sh
   podman run -it --rm registry.fedoraproject.org/fedora:34 bash
   ```

2. Download or install the prerequisite software without dependencies:

   ```sh
   dnf install -y tar bzip2 dnf-plugins-core
   curl -LO https://download-installer.cdn.mozilla.net/pub/firefox/releases/91.1.0esr/linux-x86_64/en-US/firefox-91.1.0esr.tar.bz2
   tar -C . -xjvf firefox-91.1.0esr.tar.bz2
   ```

3. Start the command:

   ```sh
   cd firefox
   ./firefox
   XPCOMGlueLoad error for file /firefox/libmozgtk.so:
   libgtk-3.so.0: cannot open shared object file: No such file or directory
   Couldn't load XPCOM.
   ```

4. Find an rpm package that provides the required file:

   ```sh
   dnf whatprovides libgtk-3.so.0
   ...
   gtk3-3.24.28-2.fc34.i686 : GTK+ graphical user interface library
   Repo        : fedora
   Matched from:
   Provide    : libgtk-3.so.0
   
   gtk3-3.24.30-1.fc34.i686 : GTK+ graphical user interface library
   Repo        : updates
   Matched from:
   Provide    : libgtk-3.so.0
   ```

5. Download and install the package:

   ```sh
   dnf download --archlist=x86_64,noarch <package name>
   rpm -Uvh --nodeps <package name>
   ```

6. Save the package name without name and architecture.
7. Repeat steps 3-6 until "cannot open shared object file" error will go.

In the end, I've created a Dockerfile that can be used as a base for other images:

```Dockerfile
FROM registry.fedoraproject.org/fedora-minimal:34
LABEL maintainer="dmisharo@redhat.com"

ENV SELENIUM_HOME=/home/selenium

WORKDIR ${SELENIUM_HOME}

RUN PACKAGES="\
        alsa-lib \
        at-spi2-atk \
        at-spi2-core \
        atk \
        avahi-libs \
        bzip2 \
        cairo \
        cairo-gobject \
        cups-libs \
        dbus-glib \
        dbus-libs \
        expat \
        fluxbox \
        fontconfig \
        freetype \
        fribidi \
        gdk-pixbuf2 \
        graphite2 \
        gtk3 \
        harfbuzz \
        imlib2 \
        java-1.8.0-openjdk-headless \
        libcloudproviders \
        libdatrie \
        libdrm \
        libepoxy \
        liberation-fonts \
        liberation-fonts-common \
        liberation-mono-fonts \
        liberation-sans-fonts \
        liberation-serif-fonts \
        libfontenc \
        libglvnd \
        libglvnd-glx \
        libICE \
        libjpeg-turbo \
        libpng \
        libSM \
        libthai \
        libwayland-client \
        libwayland-cursor \
        libwayland-egl \
        libwayland-server \
        libwebp \
        libX11 \
        libX11-common \
        libX11-xcb \
        libXau \
        libxcb \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXdmcp \
        libXext \
        libXfixes \
        libXfont2 \
        libXft \
        libXi \
        libXinerama \
        libxkbcommon \
        libxkbfile \
        libXpm \
        libXrandr \
        libXrender \
        libxshmfence \
        libXt \
        mesa-libgbm \
        nspr \
        nss \
        nss-softokn \
        nss-softokn-freebl \
        nss-util \
        pango \
        pixman \
        tar \
        tigervnc-server-minimal \
        tzdata-java \
        unzip \
        vulkan-loader \
        wget \
        xdg-utils \
        xkbcomp \
        xkeyboard-config" && \
    microdnf download -y --archlist=x86_64,noarch ${PACKAGES} && \
    rpm -Uvh --nodeps *.rpm && \
    rm -f *.rpm && \
    microdnf clean all
```

As you can see I completely ignore dependencies by providing `--nodeps` argument to `rpm` command.
Besides, I used a minimal Fedora image to even more reduce the amount of preinstalled packages.

## Init

The common practice is to run one process per container. If you need to make some IPC you do it via
networking protocols. In the case of the Selenium container image, all components have to be run in the same
container. We need three running processes: `selenium-server-standalone`, `fluxbox`
and `Xvnc`. Moreover, they should be started and finished in the right order:

`Xvnc` -> `fluxbox` -> `selenium-server-standalone`

We could use a simple shell script like this one:

```sh
#!/bin/bash

Xvnc ${DISPLAY} \
     -alwaysshared \
     -depth 16 \
     -geometry ${VNC_GEOMETRY} \
     -securitytypes none \
     -auth ${HOME}/.Xauthority \
     -fp catalogue:/etc/X11/fontpath.d \
     -pn \
     -rfbport 59$(echo ${DISPLAY} | tr -d ":") \
     -rfbwait 30000 > /dev/null 2>&1 &

sleep 3

fluxbox > /dev/null 2>&1 &

java -jar ${SELENIUM_PATH} -port ${SELENIUM_PORT} 2>&1
```

It worked fine but after a while, I discovered that `fluxbox` core dumped if you stop the container.
It doesn't affect anything but it annoyed me. I tried to gracefully handle `SIGTERM` `SIGINT` in
the script:

```sh
trap cleanup SIGTERM SIGINT

cleanup() {
    pkill java && \
    pkill fluxbox && \
    pkill Xvnc
}
```

But it didn't work for me. For some reason init script didn't stop the processes in the right order
and `fluxbox` continued causing core dump. Then I decided to write a simple init program in Go lang
that would do exactly what I want. Here it is:

```go
package main

import (
    "bufio"
    "fmt"
    "io"
    "net"
    "os"
    "os/exec"
    "os/signal"
    "syscall"
    "time"
)

func startXvnc() *exec.Cmd {
    xvnc := exec.Command(
        "Xvnc",
        os.Getenv("DISPLAY"),
        "-alwaysshared",
        "-depth",
        "16",
        "-geometry",
        os.Getenv("VNC_GEOMETRY"),
        "-securitytypes",
        "none",
        "-auth",
        fmt.Sprintf("%s/.Xauthority", os.Getenv("HOME")),
        "-fp",
        "catalogue:/etc/X11/fontpath.d",
        "-pn",
        "-rfbport",
        os.Getenv("VNC_PORT"),
        "-rfbwait",
        "30000")
    fmt.Println("Starting Xvnc")
    xvnc.Start()
    return xvnc
}

func waitForPort() {
    n := 1
    address := net.JoinHostPort("localhost", os.Getenv("VNC_PORT"))
    for n < 50 {
        conn, _ := net.Dial("tcp", address)
        if conn != nil {
            conn.Close()
            break
        }
        n++
        time.Sleep(10 * time.Millisecond)
    }
}

func startFluxbox() *exec.Cmd {
    fluxbox := exec.Command("fluxbox")
    fmt.Println("Starting fluxbox")
    fluxbox.Start()
    return fluxbox
}

func printSeleniumCombinedOutput(seleniumStdout io.ReadCloser) {
    scanner := bufio.NewScanner(seleniumStdout)
    for scanner.Scan() {
        line := scanner.Text()
        fmt.Println(line)
    }
}

func startSelenium() *exec.Cmd {
    fmt.Println("Starting selenium standalone")
    selenium := exec.Command("java", "-jar", os.Getenv("SELENIUM_PATH"), "-port", os.Getenv("SELENIUM_PORT"))
    seleniumStdout, _ := selenium.StdoutPipe()
    selenium.Stderr = selenium.Stdout
    go printSeleniumCombinedOutput(seleniumStdout)
    selenium.Start()
    return selenium
}

func startProcesses() (*exec.Cmd, *exec.Cmd, *exec.Cmd) {
    xvnc := startXvnc()
    waitForPort()
    fluxbox := startFluxbox()
    selenium := startSelenium()
    return xvnc, fluxbox, selenium
}

func waitForSignals() {
    sigs := make(chan os.Signal, 1)
    signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
    <-sigs
}

func stopProcesses(xvnc *exec.Cmd, fluxbox *exec.Cmd, selenium *exec.Cmd) {
    fmt.Println("Stopping selenium")
    selenium.Process.Kill()
    selenium.Wait()
    fmt.Println("Stopping fluxbox")
    fluxbox.Process.Kill()
    fluxbox.Wait()
    fmt.Println("Stopping Xvnc")
    xvnc.Process.Kill()
    xvnc.Wait()
}

func main() {
    xvnc, fluxbox, selenium := startProcesses()
    waitForSignals()
    stopProcesses(xvnc, fluxbox, selenium)
    fmt.Println("Bye bye")
    os.Exit(0)
}
```

I like Go for its simplicity and one binary output. This small init program solved the issue
with `fluxbox`. Using multi-stage image building we can compile the init program in of the
preliminary stages:

```Dockerfile
FROM docker.io/library/golang:1.17 AS builder

COPY init.go .

RUN go build init.go

FROM quay.io/redhatqe/selenium-base:latest

COPY --from=builder /go/init /usr/bin/

RUN chmod +x /usr/bin/init

CMD ["init"]
```

### Results

Let's compare image sizes:

```sh
podman pull docker.io/selenium/standalone-firefox:latest quay.io/redhatqe/selenium-standalone:latest
podman images
REPOSITORY                              TAG     IMAGE ID        CREATED     SIZE
docker.io/selenium/standalone-firefox   latest  d1f4408519cd    3 days ago  998 MB
quay.io/redhatqe/selenium-standalone    latest  2562f5b2819d    10 days ago 902 MB
```

As you can see `quay.io/redhatqe/selenium-standalone:latest` has lesser size than
`docker.io/selenium/standalone-firefox:latest`. Keep in mind that our image contains both Firefox
and Chrome browsers. I think it makes sense to have a separate image per a browser. This will
give us thinner images.

References:

* <https://github.com/RedHatQE/selenium-images>
* <https://quay.io/repository/redhatqe/selenium-standalone>
* <https://quay.io/repository/redhatqe/selenium-base>
* <https://github.com/SeleniumHQ/docker-selenium>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/21)
