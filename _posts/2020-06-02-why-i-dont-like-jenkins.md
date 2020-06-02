---
layout: post
title: Why I don't like Jenkins
tags: [jenkins, ci]
---
I guess everybody knows Jenkins. It's one of the oldest and well-known automation system. It
was developed in the times when there was no Docker, Kubernetes, cloud native and other buzzwords. I
familiarized with it when I started to work at Red Hat. After a couple years of using I have some
concerns I want to share.

## UI

User interface it's a first thing that you see in software with GUI. Jenkins has archaic, slow and
unobvious user interface. If you have installed a bunch of plugins your settings page will become a
mess.  In modern browsers some forms are just broken:

{% picture assets/img/2020-06-02-why-i-dont-like-jenkins-1.png --alt Jenkins Classic UI %}

There is more modern UI from Jenkins developers called Blue Ocean. It looks much nicer but it
doesn't have feature parity with the classic UI. So it can be used only for pipeline displaying.

{% picture assets/img/2020-06-02-why-i-dont-like-jenkins-2.png --alt Jenkins Blue Oxean UI %}

## Scalability

Jenkins is distributed as one .war binary. It's supposed to be executed on some machine with java
installed. If you have a lot of jobs and users you are in trouble. Jenkins cannot scale. You will
end up spreading your jobs among several Jenkins instances.

## Pipeline syntax

This one is controversial. Pipelines can described via declarative syntax or jenkins job DSL which
is built on top of Groovy.

### Declarative

In my opinion declarative syntax looses to yaml based pipelines. It tends to have deep nested
structures which are hardly to read. Let's take an example from the official documentation:

```text
pipeline {
  agent { docker 'maven:3-alpine' }
  stages {
    stage('Example Build') {
      steps {
        sh 'mvn -B clean verify'
      }
    }
  }
}
```

You can see here is 4 nested parenthesis. Compare with possible Gitlab CI config:

```yaml
image: maven:3-alpine
stages:
  - test
testing:
  stage: tests
  script:
  - mvn -B clean verify
```

Don't get me wrong I'm not a yaml fan but in the most cases yaml looks more "declarative" than
Jenkins declarative syntax

### Scripted

This may be the most powerful feature of Jenkins. You can implement any logic in your pipelines.
But in the end you will quickly discover that Groovy code which is executed somewhere in the Jenkins
guts almost not possible to debug. Really the only thing you can do is just put `println`. Therefore
take my advice do not try to implement any complex workflows. Make it as much simple as possible.

## Documentation

I think Jenkins has bad documentation. At least everything that relates to pipeline. Not all aspects
covered in <https://www.jenkins.io/doc/book/pipeline/> and often I need to search something in the
Internet.

I'm convinced that Jenkins is in the end of its lifecycle. The industry have changed but Jenkins
almost has not. Its plugin system extended its life but the retirement is coming. You can still use
it for small projects but highly recommend to look at its competitors if you start a new project.
