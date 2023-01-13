---
title: UI testing in Kubernetes
tags: k8s, selenium, testing
---
As a quality engineer I responsible for testing various parts of a product. One of such part can be
the web UI. But before your first UI test will be executed you will need to configure a lot of
things. It might be a non-trivial task. Kubernetes can be quite helpful here and be actual
"one ring to rule them all".

## High-level overview

Let's consider a typical setup of UI testing with Jenkins as a CI system:

<img class="image-center" alt="diagram 1" src="{static}/assets/img/2020-05-02-ui-testing-in-kubernetes-1.png"/>

1. Jenkins server initializes a test session and sends the job configuration to a jenkins agent.
2. Jenkins agent executes shell commands specified in the job.
3. These commands usually run tests from some tests suite.
4. When a UI test starts it communicates with a selenium server in order to perform actions in the
browser.
5. Selenium server sends commands to a specific browser driver and then browser open urls, click
buttons and so on.
6. If you want to observe how your test is running you can configure a VNC server and connect to it
with any VNC client.

## Selenium and containers

You can run selenium in a standalone mode on your machine but that setup has some disadvantages. For
example it's quite problematically to have installed several versions of a browser. Docker brings
a significant improvement into web UI testing. Now you can have various images with required browser
versions. Besides, containers don't persist the state. It means every test session starts in the
same conditions and doesn't affect on next ones.

## Jenkins and Kubernetes

Nowadays more and more routines are adopted to be run in Kubernetes and various CI systems are not
an exception. I've already mentioned Jenkins here so let's continue talk about that automation
server. Jenkins has [kubernetes plugin](https://github.com/jenkinsci/kubernetes-plugin) that
dynamically spawns agents in a kubernetes cluster. This approach may give us some new ideas about
how to run tests. As you may know kubernetes operates
[pods](https://kubernetes.io/docs/concepts/workloads/pods/pod/). Think of it as a group of
containers with some shared resources such as network and mounts. So let's combine all pieces
together:

<img class="image-center" alt="diagram 2" src="{static}/assets/img/2020-05-02-ui-testing-in-kubernetes-2.png"/>

We can describe this setup in a `podTemplate` of jenkins job DSL:

```groovy
podTemplate(containers: [
    containerTemplate(
        name: "jenkins-agent",
        image: "jenkins/jnlp-slave",
        args: '${computer.jnlpmac} ${computer.name}'
    ),
    containerTemplate(
        name: "tests-suite",
        image: "some_tests_suite_image",
        ttyEnabled: true,
        command: "cat"
    ),
    containerTemplate(
        name: "selenium",
        image: "selenium/standalone-firefox-debug"
    )
]) {
    node(POD_LABEL) {
        ...
    }
}
```

or via more familiar YAML:

```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    some-label: some-label-value
spec:
  containers:
  - name: jenkins-agent
    image: jenkins/jnlp-slave
    args:
        - '\$(JENKINS_SECRET)'
        - '\$(JENKINS_NAME)'
  - name: tests-suite
    image: some_tests_suite_image
    tty: true
    command: ["cat"]
  - name: selenium
    image: selenium/standalone-firefox-debug
```

Jenkins Kubernetes plugin and this pod configuration can be in some way an alternative of
[Selenium Grid](https://www.selenium.dev/documentation/en/grid/). There is a one notable moment
about Jenkins jobs. They can be
[parallelized](https://www.jenkins.io/doc/pipeline/examples/#parallel-multiple-nodes) across
multiple Jenkins nodes. In that case each node will have its own selenium instance.

Pros:

* you don't need to setup and maintain complex Selenium Grid architecture;
* the latency is minimal because both tests suite and selenium containers are running in the same
pod;

Cons:

* you have to implement a job paralellizer in jenkins dsl;
* you lose Selenium Grid dashboard;

## Summary

As you may see Kubernetes and containers are game changers. They give you more room to maneuver.
In this post I described one possible scenario of the usage but there are other attempts to adapt
Selenium to run in Kubernetes such as [Moon](https://aerokube.com/moon/latest/),
[Zalenium](https://opensource.zalando.com/zalenium/) and
[Callisto](https://github.com/wrike/callisto).
