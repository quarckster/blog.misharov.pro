---
layout: post
title: Making a Kodi add-on repository
tags: [kodi, netlify]
---
In this post I'll explain how to create your own Kodi add-on repository, deploy it on Netlify and
automate that workflow.

## Kodi

Kodi is a popular open source multimedia center. It has a huge add-ons ecosystem which can extend
functionality significantly. Add-ons are distributed as regular zip archives and you can install it
via Kodi UI just specifying a path in your filesystem. That approach has one disadvantage. If you
want to update add-on version you have to do it manually. I mean you should follow updates of the
add-on, download and install it every time.

In order to get rid off all of these manual actions we can create an add-ons repository and enable
it in Kodi.

## Repository add-on structure

According to [Kodi wiki](https://kodi.wiki/view/Add-on_repositories) an add-on repo should have some
add-ons, a master xml file and a checksum of that file. Directory structure should look like this:

```text
repo_dir
├── addons.xml
├── addons.xml.md5
└── addon.id
    └──addon.id-x.y.z.zip
...
└── addon2.id
    └── addon2.id-x.y.z.zip
```

You can also put a repository add-on for distribution. This allows you to share your repository with
others.

## Hosting

Add-on repository should be hosted on some web server. Static content hosting services such as
Github Pages or Netlify perfectly fit for this task. I prefer Netlify because it gives more control
for the deployment and its starter tariff plan is more than enough for our purposes. By the way
this blog is also hosted on Netlify.

Netlify provides a nice CLI tool for the deployment. First you should install `netlify-cli`. It's
a javascript application so we use `npm` here:

```sh
$ npm install netlify-cli
$
```

Then you can deploy a local folder to your site in the following way:

```sh
$ node_modules/netlify-cli/bin/run deploy --dir=your_directory \
                                          --prod \
                                          --auth="$NETLIFY_AUTH_TOKEN" \
                                          --site="$NETLIFY_SITE_ID"
$
```

`$NETLIFY_AUTH_TOKEN` and `$NETLIFY_SITE_ID` you will find in Netlify settings. After that your
static files will be accessible via Internet. That's exactly what we need for making Kodi add-on
repository.

## Live example

I created a Kodi add-on for one streaming service and in one day I decided to create an add-on
repository. I already had configured Travis CI and build script. I was need to extend it a bit.
A release pipeline is very simple:

```text
git push origin some_tag -> lint -> test -> deploy
```

In `deploy` stage an add-on archive is created and attached to Github Release as an asset. I
split it on `deploy_github` and `deploy_netlify`. In `deploy_netlify` the build script generates a
repo directory, put required files there and uploads everything to Netlify using `netlify-cli`.
Resulting pipeline:

```text
git push origin some_tag -> lint -> test -> deploy_github -> deploy_netlify
```

And the build script `make.sh`:

```bash
#!/bin/bash
# I omitted the body of functions to show the idea.
# Full source can be found in the references below.

function check_version() {
    ...
}

function build_video_addon() {
    check_version $1
    echo "Creating video.kino.pub add-on archive"
    echo "======================================"
    ...
}

function build_repo_addon() {
    echo "Creating repo.kino.pub add-on archive"
    echo "====================================="
    ...
}

function create_repo() {
    build_video_addon $1
    build_repo_addon
    echo "Creating repository add-on directory structure"
    echo "=============================================="
    ...
}

function deploy() {
    create_repo $1
    echo "Deploying files to Netlify"
    echo "=========================="
    node_modules/netlify-cli/bin/run deploy --dir=repo \
                                            --prod \
                                            --auth="$NETLIFY_AUTH_TOKEN" \
                                            --site="$NETLIFY_SITE_ID"
}

"$@"
```

In `deploy_github` CI runs `bash make.sh build_video_addon` and uploads the archive to Github. Then
in `deploy_netlify` `bash make.sh deploy` is called.

As you can see creating a Kodi add-on repository is a quite trivial task and updating it can be
easily automated.

References:

* <https://kodi.tv>
* <https://kodi.wiki/view/Add-on_development>
* <https://kodi.wiki/view/Add-on_repositories>
* <https://www.netlify.com/>
* <https://github.com/quarckster/kodi.kino.pub>
