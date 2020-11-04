---
layout: post
title: Migrating Jenkins jobs to new instance
tags: [jenkins, migration, backup]
---
You might know [Why I don't like Jenkins]({% post_url 2020-06-02-why-i-dont-like-jenkins %}) but I
still have to use it in my job. Recently I was need to migrate Jenkins jobs to new instance and it
was easier than I expected.

## Prerequisites

I had two Jenkins instances on different OpenShift clusters. Both instances have mounted persistent
volumes where the content of `/var/lib/jenkins` directories is stored. I got a task to migrate all
jobs, configs and secrets to the new instance. I've never done that before so I went the dumbest
way I could figure out.

## Jobs migration

Jenkins jobs are stored in `/var/lib/jenkins/job` so I decided just to copy it to some intermediate
storage. We use regular OpenShift Jenkins deployment so `rsync` was installed into the image. In
order to copy files between an OpenShift pod and the local machine `oc rsync` command should be
used. So here is my step by step guide:

1. Use a machine with enough free space and fast connection.
2. Login to first OpenShift cluster:

   ```sh
   oc login --token=some_token --server=ocp_api_url
   ```

3. Switch the namespace and copy `/var/lib/jenkins/jobs`:

    ```sh
    oc project your_jenkins_project
    oc rsync jenkins-pod-name:/var/lib/jenkins/jobs/ /some/local/directory
    ```

4. Login to another OpenShift cluster.
5. Switch namespace and copy `/some/local/directory` to the jenkins pod:

    ```sh
    oc project your_jenkins_project
    oc rsync /some/local/directory jenkins-pod-name:/var/lib/jenkins/jobs/
    ```

6. Restart Jenkins on the second cluster.

An that's it. You even don't need to stop first Jenkins instance. Actually if it was need to do it
would make the process more complicated. You can access data stored in PVCs only via pods that mount
them somewhere in the filesystem.

## Secrets migration

All of our jobs use Jenkins secrets engine. Without secrets from the first instance jobs wouldn't
work. Fortunately, secrets migration was just about copying files. I found a helpful guide on
[itsecureadmin.com](https://itsecureadmin.com):

1. Remove the `identity.key.enc` file on second instance:

    ```sh
    rm /var/lib/jenkins/identity.key.enc
    ```

2. Using `oc rsync` replace `secret*` `credentials.xml` files from first Jenkins instance to second
   one.
3. Restart Jenkins on the second cluster.
4. ...
5. PROFIT!

## References

* <https://itsecureadmin.com/2018/03/jenkins-migrating-credentials/>
