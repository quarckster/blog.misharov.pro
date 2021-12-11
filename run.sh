#!/bin/bash

podman run -it -e BUNDLE_BIN=/mnt/vendor/bundle/bin \
               -e BUNDLE_PATH=/mnt/vendor \
               -w /mnt \
               -v .:/mnt \
               -p 4000:4000 docker.io/library/ruby:2.7 \
               bundle exec jekyll serve -H 0.0.0.0

