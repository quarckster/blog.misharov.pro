---
layout: post
title: Building and deploying static websites using Openshift, S2I and Gitlab CI
tags: [s2i, openshift, gitlab ci]
---
Using Gitlab CI, Openshift and S2I technologies you can create a pipeline for building and deploying
static websites.

## Prerequisites

We have two repositories that are hosted on Gitlab:

* `https://gitlab.example.com/data-script`
  
  Contains a script that generates a bunch of JSON files

* `https://gitlab.example.com/frontend`

  Contains a React application that consumes JSON files

The web site is deployed on Openshift Container Platform, therefore we will leverage its features:

* Build Configs
* S2I
* Deployments (strictly speaking it's a native K8S resource)
* Routes

The task is to create a Gitlab CI pipeline that would build and deploy the static website when a tag
is pushed into one of the repositories.

{:refdef: style="text-align: center;"}
![diagram 1](/assets/img/2021-05-23-s2i-static-sites-1.png)
{:refdef}
{:refdef: style="text-align: center;"}
*diagram 1*
{:refdef}

## Manifests

### Dockerfiles

We are going to deploy the web site on OCP and we need to build a container image that will contain
all required assets of our web sites. Let's start from `data-script`. During the image building we
need to generate a bunch JSON files. We need only JSONs and nothing else therefore we will use
multistaging building and `scrath` image:

```Dockerfile
FROM registry.access.redhat.com/ubi8/ubi:8.4 AS builder

ENV HOME=/data_script/

WORKDIR $HOME

# install python
RUN dnf install --nodocs -y python38 python38-pip && \
    python3 -m venv /data_script_venv

ENV PATH="/data_script_venv/bin:$PATH"
COPY . .

# generate JSON files
RUN pip install -U --no-cache-dir pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    mkdir jsons && \
    python main.py

# we don't need anything, this container image is just an artifacts storage
FROM scratch

COPY --from=builder /data_script/jsons /artifacts
```

`frontend` follows the similar approach. We generate the assets and put them into a `scratch` image:

```Dockerfile
FROM registry.access.redhat.com/ubi8/ubi:8.4 AS builder

ENV HOME=/frontend/

WORKDIR $HOME

COPY . .

# install nodejs and npm
RUN dnf install --nodocs -y npm && \
    npm install && \
    npm run build 

FROM scratch

COPY --from=builder /frontend/dist /artifacts
```

### Build configs

`Build Config` is an Openshift resource that has instructions how to build an application. It has
various strategies but in our case we will use `Docker` and `Source` strategies. `Docker` strategy
is used for building artifacts images. Both of them are pretty the same:

```yaml
kind: BuildConfig
apiVersion: build.openshift.io/v1
metadata:
  # name: frontend-artifacts
  name: json-artifacts
  labels:
    app: demo
spec:
  output:
    to:
      kind: DockerImage
      # for frontend it would have this value
      # name: some-registry/static-website:frontend-artifacts
      name: some-registry/static-website:data-artifacts
    pushSecret:
      name: some-push-secret
  # it's a good practice to specify resource constraints
  resources:
    requests:
      memory: 256Mi
      cpu: 250m
    limits:
      memory: 512Mi
      cpu: 500m
  successfulBuildsHistoryLimit: 1
  failedBuildsHistoryLimit: 1
  strategy:
    # The quote from the Openshift documentation:
    # The docker build strategy invokes the docker build command, and it expects a repository with a
    # Dockerfile and all required artifacts in it to produce a runnable image
    type: Docker
  source:
    type: Git
    git:
      # frontend application lives here
      # uri: https://gitlab.example.com/frontend
      uri: https://gitlab.example.com/data-script
```

The runnable image is built using `Source` strategy. This strategy uses so called S2I images in
order to produce runnable images without any `Dockerfile`. We will use
`registry.redhat.io/rhel8/nginx-118` S2I image for building a container with `nginx` that serves
static files from our artifacts images:

```yaml
kind: BuildConfig
apiVersion: build.openshift.io/v1
metadata:
  name: runner
  labels:
    app: demo
spec:
  output:
    to:
      kind: DockerImage
      name: some-registry/static-website:runner
    pushSecret:
      name: some-push-secret
  resources:
    requests:
      memory: 256Mi
      cpu: 250m
    limits:
      memory: 512Mi
      cpu: 500m
  successfulBuildsHistoryLimit: 1
  failedBuildsHistoryLimit: 1
  strategy:
    # During the building assets from artifacts images are copied inside
    # registry.redhat.io/rhel8/nginx-118 and s2i assembly scripts are executed
    type: Source
    sourceStrategy:
      from:
        kind: DockerImage
        name: registry.redhat.io/rhel8/nginx-118
      pullSecret:
        name: some-pull-secret
  source:
    type: Image
    images:
      - from:
          kind: DockerImage
          name: some-registry/static-website:data-artifacts
        paths:
        # we copy artifacts into the working directory
          - sourcePath: /artifacts
            destinationDir: .
      - from:
          kind: DockerImage
          name: some-registry/static-website:frontend-artifacts
        paths:
          - sourcePath: /artifacts
            destinationDir: .
  runPolicy: Serial
```

## Deployment

Here is `Delpoyment` manifest of our static web site:

```yaml
kind: Deployment
apiVersion: apps/v1
metadata:
  name: static-web-site
  labels:
    app: demo
spec:
  revisionHistoryLimit: 2
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      name: demo
  template:
    metadata:
      name: demo
      labels:
        name: demo
    spec:
      volumes:
        - name: demo-config-map
          configMap:
            name: demo
            defaultMode: 420
      containers:
        - name: runner
          image: some-registry/static-website:runner
          # this is important because the image tag is floating and we need to always pull the
          # image on every container spawning
          imagePullPolicy: Always
          resources:
            limits:
              cpu: 200m
              memory: 200Mi
            requests:
              cpu: 100m
              memory: 100Mi
          volumeMounts:
            # nginx requires some configuration
            - name: demo-config-map
              mountPath: /opt/app-root/etc/nginx.d
```

`nginx` requires a configuration for our static web site. We will store it in a `Config Map` and
mount it into the container:

```yaml
kind: ConfigMap
apiVersion: v1
metadata:
  name: demo
  labels:
    app: demo
data:
  demo.conf: |
    server {
      server_name _;
      listen 8081 default_server;
      root /opt/app-root/src/;
      location / {
# we put all assets into "artifacts" directory
# and here we tell nginx where is the root of our
# static web site
        root /opt/app-root/src/artifacts;
        try_files $uri /index.html;
      }
    }
```

### Route

The networking part is small. We need `Service` and `Route` manifests after that our static web
site is ready:

```yaml
kind: Service
apiVersion: v1
metadata:
  name: demo
  labels:
    app: demo
spec:
  ports:
    - protocol: TCP
      port: 8081
      targetPort: 8081
  # Don't forget about correct pods selector
  selector:
    name: demo
```

```yaml
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: demo
  labels:
    app: demo
spec:
  host: demo.example.com
  to:
    kind: Service
    name: demo
  port:
    targetPort: 8081
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
```

## Pipeline

We have all manifests in place and we applied the to Openshift using `oc apply -f` command. The next
step is to set up Gitlab CI pipelines that trigger builds and update the deployment. Here is the
content of `.gitlab-ci.yml` for `data-script` repository:

```yaml
stages:
  - Testing
  - Build artifacts
  - Build runner
  - Rollout runner

testing:
  # tests must pass before building artifacts
  image: some-registry/your-builder:latest
  stage: Testing
  script:
    - test.sh
  tags:
    - shared

build-artifacts:
  image: quay.io/openshift/origin-cli:latest
  stage: Build artifacts
  script:
  # oc utility has a nice feature to show the build logs
  # and return the status code after finishing building
    - |
      oc --server=<openshift-api-url> \
         --namespace=<namespace> \
         --token=$PIPELINE_TOKEN \
         start-build json-artifacts --wait --follow
  # start-build frontend-artifacts --wait --follow
  # for https://gitlab.example.com/frontend repo
  tags:
    - shared
  only:
    - tags

build-runner:
  image: quay.io/openshift/origin-cli:latest
  stage: Build runner
  script:
    - |
      oc --server=<openshift-api-url> \
         --namespace=<namespace> \
         --token=$PIPELINE_TOKEN \
         start-build runner --wait --follow
  tags:
    - shared
  only:
    - tags

rollout-runner:
  image: quay.io/openshift/origin-cli:latest
  stage: Rollout runner
  script:
  # in order to upgrade the image
  # we just delete all pods with certain labels
  # replica set automatically spawns a new pod
  # with new image because we set Image Pull Policy:
  # Always
    - |
      oc --server=<openshift-api-url> \
         --namespace=<namespace> \
         --token=$PIPELINE_TOKEN \
         delete pod -l name=demo
  # waiting until all pods are ready
      oc --server=<openshift-api-url> \
         --namespace=<namespace> \
         --token=$PIPELINE_TOKEN \
         wait --for=condition=Ready pod -l name=demo --timeout=60s
  tags:
    - shared
  only:
    - tags
```

## Summary

Gitlab CI and Openshift offer vast of possibilities in building and deploying. I showed you a case
with two repositories. In my opinion it's not so common. Usually we deal with one repository, for
example it could be `sphinx` based documentation. Nevertheless I think it's a good show case of
`Source` build strategy and `S2I` approach. It demonstrates that we can consume building artifacts
from more than one container image. I would concern about loads of yamls but we cannot do much with
it. This format is standard de-facto in CI and devops world.

References:

* <https://docs.openshift.com/container-platform/4.7/openshift_images/using_images/using-s21-images.html>
* <https://docs.openshift.com/container-platform/4.7/cicd/builds/understanding-image-builds.html>
* <https://docs.gitlab.com/ee/ci/yaml/README.html>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/16)
