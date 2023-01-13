---
title: Triggering Kubernetes resources in OpenShift
tags: openshift, deployments, triggers, k8s
---
When I was starting to familiarize with OpenShift 3 I loved its builtin continous delivery
mechanism. Using webhooks and triggers you can easily deploy your code from Github, GitLab or
Bitbucket. In OpenShift 4 more Kubernetes resources have been added and they don't have triggers
support. Is there a way to enable it?

## Triggers

Let me shortly explain what are triggers. Generally speaking it's just a section in yaml
that describes events inside the cluster that should drive the creation of new deployment processes.

Some examples:

```yaml
triggers:
  - type: "ConfigChange"
```

This trigger starts a new roll-out when we change DeploymentConfig spec.

```yaml
triggers:
  - type: "ImageChange"
    imageChangeParams:
      automatic: true
      from:
        kind: "ImageStreamTag"
        name: "some_image:latest"
        namespace: "myproject"
```

This trigger is more interesting. It starts a new roll-out when an image is updated in a certain
image stream.

The issue here is `triggers` only defined in `DeploymentConfig` which is OpenShift specific. If you
want to use them for Kubernetes resources such as `Deployment` you have to configured it
differenetely.

## Annotations

OpenShift developers propose to add image change triggers into annotations. There is an especial
annotation `image.openshift.io/triggers`:

```yaml
image.openshift.io/triggers: '[{"from":{"kind":"ImageStreamTag","some_image":"latest"},"fieldPath":"spec.template.spec.containers[?(@.name==\"myapp\")].image"}]'
```

Fortunately, you don't have to remember this structure just `oc` command:

```sh
$
oc set triggers deployment/myapp --from-image some_image:latest -c myapp
```

This command adds required annotation into your `Deployment`.

## References

* <https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/>
* <https://developers.redhat.com/blog/2019/09/20/using-red-hat-openshift-image-streams-with-kubernetes-deployments/>
* <https://docs.openshift.com/container-platform/3.11/dev_guide/deployments/basic_deployment_operations.html#triggers>
