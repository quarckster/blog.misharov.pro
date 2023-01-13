---
title: Gitlab CI shared pipelines
tags: gitlab, ci, testing
---
Imagine you have a group of repositories in Gitlab and you would like to have the same pipelines
for whole group.

## Includes

The first thing that would come on your mind it's storing a pipeline configuration in a dedicated
git repository and then somehow consume it. Something similar has Jenkins for its scripted
pipelines. Gitlab developers thought in the same direction and introduced `include` keyword. It
supports several inclusion methods: local, file, remote and template.

### Local

Let's say you have a repository with the following file structure:

```txt
some_repository
├── .gitlab-ci.yml
├── lint.yml
├── tests.yml
└── deploy.yml
```

You can split your pipeline config on several files where an each file represents a stage. Using
`include:local` method it's possible to include content of the files in the same repository:

```yaml
include:
  - local: /lint.yml
  - local: /tests.yml
  - local: /deploy.yml
```

### File

`include:file` will be useful when you want to include a pipeline config from a different repository
under the same Gitlab instance.

```yaml
include:
  - project: my-group/some_repository
    file: '/.gitlab-ci.yml
```

It's possible to specify ref which makes it very similar to [Jenkins' shared pipelines mechanism](https://www.jenkins.io/doc/book/pipeline/shared-libraries/#using-libraries):

```yaml
include:
  - project: my-group/some_repository
    ref: stable
    file: '/.gitlab-ci.yml
```

### Remote

`include:remote` purpose is to include a pipeline config from an arbitrary git repository:

```yaml
include:
  - remote: 'https://gitlab.com/awesome-project/raw/master/.gitlab-ci-template.yml'
```

It's not very clear if you can specify a certain ref.

### Template

Gitlab Ci comes with some [predefined](https://gitlab.com/gitlab-org/gitlab/tree/master/lib/gitlab/ci/templates)
pipeline configs and you can include them using `include:template`:

```yaml
include:
  - template: Auto-DevOps.gitlab-ci.yml
```

## Nested includes

One of cool features of `include` is that you can nest this directive. According to documentation
100 nested includes is allowed. For example we have two repositories with the following file
structures:

```txt
shared-pipeline
├── all.yml
├── lint.yml
├── tests.yml
└── deploy.yml
```

```txt
my-python-project
├── src
├── tests
├── .gitlab-ci.yml
└── README.md
```

Then we can nest includes:

`my-python-project/.gitlab-ci.yml`:

```yaml
- project: my-group/shared-pipeline
  ref: master
  file: /all.yml
```

`shared-pipeline/all.yml`:

```yaml
include:
  - local: /lint.yml
  - local: /tests.yml
  - local: /deploy.yml
```

## With great power comes great responsibility

Awesome, we reduced redundancies and kept our code "DRY". But now we have a new challenge. Imagine
we have dozens projects that use our shared pipeline config and if we break something in there we
break all pipelines in dependant repositories. Obviously we need to test our changes before we merge
them. It's kind of a tricky task because simple yaml lint test is not enough we need to run our
changes against a real repository.

### Testing repository

I encountered with that problem and I decided to create a separate Gitlab repository in order to
test changes in shared pipeline library. So here are the prerequisites:

* a shared Gitlab pipeline config repo: `https://gitlab.com/acme/shared-pipeline-lib`
* a testing repository: `https:/gitlab.com/acme/pipeline-test`
* a user who wants to change `shared-pipeline-lib`: `some_user`

And here are the steps that you need to perform to test your MR:

1. Create a merge request to `https://gitlab.com/acme/shared-pipeline-lib`.
2. Clone `pipeline-test` repo:

    ```sh
    git clone git@gitlab.cee.redhat.com:insights-qe/pipeline-test.git
    ```

3. Create a branch in `pipeline-test` repo with the following name:
`your_name/merge_request_branch_name`, e.g. `some_user/my_awesome_changes`:

    ```sh
    git checkout -b some_user/my_awesome_changes
    ```

4. Edit `.gitlab-ci.yml` in pipeline-test repo to point include to ref with your changes. e.g.:

    ```yaml
    include:
    - project: some_user/shared-pipeline-lib
        ref: my_awesome_changes
        file: /all.yml
    ```

5. Commit the changes and push the branch directly to https://gitlab.cee.redhat.com/insights-qe/pipeline-test:

    ```sh
    git add .gitlab-ci.yml
    git commit -m "Updated .gitlab-ci.yml"
    git push origin HEAD
    ```

6. Now you can examine changes of your MR. Pipeline should automatically start and you should be
able to see it on `https:/gitlab.com/acme/pipeline-test`

I hope you got the idea. I guess there is a space for improvement and it's possible to automate
these steps.

## References

* <https://docs.gitlab.com/ee/ci/yaml/README.html#include>