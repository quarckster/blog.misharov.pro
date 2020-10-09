---
layout: post
title: Gitlab runner in Openshift
tags: [openshift, gitlab-runner, ci]
---
I'm pretty sure most of you familiar with Gitlab. It has a lot of features and nowadays it looks a
bit bloated but one thing I really love in this tool. It's Gitlab CI. One of the coolest thing there
is it can run jobs on many platforms including virtual machines, Docker containers and Kubernetes.

## Gitlab CI

Let's look in detail how Gitlab CI works and configured.

**Gitlab runner** is an agent which communicates with Gitlab server, receives tasks from it and
executes them on a selected executor. You can install the runner on any linux host or put it into a
container.

**Executor** is an environment where the code will be ran. Here is a list of available executors:
SSH, Shell, VirtualBox, Parallels, Docker, Kubernetes and Custom.

I would like to pay more attention to Kubernetes executor. When Gitlab runner is configured to use
this executor it spawns pods in a Kubernetes cluster and jobs from pipelines are executed inside the
pods. You can install a runner to your cluster via Gitlab web UI just clicking one button. But it
assumes that you have cluster admin privileges. Moreover if you have an Openshift cluster you should
take in account some its "features".

## Openshift

Now let's talk about Openshift. It's a Kubernetes distribution which is developed by Red Hat. It has
more advanced security policies and provides some custom objects such as DeploymentConfigs,
BuildConfigs, ImageStreams and others. Openshift has also Templates API. It's something similar to
Helm charts but less flexible and only Openshift specific. Nevertheless Openshift templates are a
convenient way to pack all objects which are related to one service in one YAML file.

## Gitlab runner template

So I decided to create such [template](https://github.com/RedHatQE/ocp-gitlab-runner) for Gitlab
runner. Let me explain what objects are created and a deployment workflow.

1. The following objects are created:
    * `gitlab-runner-config-map` ConfigMap;
    * `gitlab` ServiceAccount;
    * `gitlab-rb` RoleBinding for `gitlab` ServiceAccount;
    * `gitlab-runner` BuildConfig;
    * `gitlab-runner` ImageStream;
    * `gitlab-helper` BuildConfig;
    * `gitlab-helper` ImageStream;
    * `gitlab-runner` DeploymentConfig.
2. When image is changed in `gitlab-runner` ImageStream `gitlab-runner` DeploymentConfig is started.
3. Two init containers are spawned:
    * `busybox` copies `config.toml` from `gitlab-runner-config-map` ConfigMap to a shared volume
named `data`;
    * `gitlab-runner-init` container registers a runner for a given Gitlab instance and changes
`config.toml` in the shared volume `data`.
4. Finally a pod with `gitlab-runner` container starts with `config.toml` which is mounted from the
shared volume `data`.

After that you will see a new entry in the UI under `Settings`/`CI / CD`/`Runners`.

## Usage

There are two ways how you can apply this template: via web UI or CLI. In the UI you just need to
copy and paste the content of `ocp-gitlab-runner-template.yaml` into `Import YAML` dialog. Then
instantiate the template in order to create the objects. For command line interface you should use
`oc` utility:

```shell
$ oc process -f ocp-gitlab-runner-template.yaml \
    -p NAME="gitlab-runner" \
    -p CI_SERVER_URL="URL of a Gitlab REST API" \
    -p REGISTRATION_TOKEN="Runner's registration token" \
    -p CONCURRENT="The maximum number of concurrent CI pods" \
    | oc create -f -
```

That's it. I hope someone find it useful and feel free to use it.

## References

* [Gitlab](https://gitlab.com)
* [Openshift](https://www.openshift.com/)
* [GitLab CI/CD docs](https://docs.gitlab.com/ee/ci/)
* [Openshift templates docs](https://docs.openshift.com/container-platform/4.4/openshift_images/using-templates.html)
* [OCP Gitlab runner repository](https://github.com/RedHatQE/ocp-gitlab-runner)
* [Helm](https://helm.sh/)
