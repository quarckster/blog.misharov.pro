---
layout: post
title: OAuth in OpenShift
tags: [openshift, oauth]
---
Applications provisioned in OpenShift can use its OAuth authentication mechanism for granting
access. This is very useful feature because all applications running on OpenShift will have
consistent behavior. But there might be some caveats if you don't understand fully how OAuth works.

## OAuth

OAuth 2.0 is a quite complex authorization framework that allows a third-party application to obtain
limited access to an HTTP service. The very first step in authorization flow is a sending request
to authorization endpoint:

```txt
GET {Authorization Endpoint}
  ?response_type=code             // - Required
  &client_id={Client ID}          // - Required
  &redirect_uri={Redirect URI}    // - Conditionally required
  &scope={Scopes}                 // - Optional
  &state={Arbitrary String}       // - Recommended
  &code_challenge={Challenge}     // - Optional
  &code_challenge_method={Method} // - Optional
  HTTP/1.1
HOST: {Authorization Server}
```

OpenShift allows you to configure a service account as an OAuth client. When using a service account
as an OAuth client:
  
* `client_id` is `system:serviceaccount:<service_account_namespace>:<service_account_name>`;
* `redirect_uri` must match an annotation on the service account.

This is quite important information that you might need for your OpenShift administration routines.

## Again Jenkins

OpenShift comes with a bunch of services that you can provision in one click. Jenkins is one of such
services. Moreover, it's well integrated and supports authentication using OpenShift OAuth. During
provisioning all required resources are created automatically including Deployment Config, Service
Account, Service, Route and others. After the provisioning your Jenkins instance will be
available on such URL `https://jenkins-your-namespace.apps.example.com`. But before you get to
Jenkins UI the very first request will be send to OpenShift authorization endpoint:

```txt
https://oauth-openshift.apps.example.com/oauth/authorize
  ?client_id=system:serviceaccount:your-namespace:jenkins
  &redirect_uri=https://jenkins-your-namespace.apps.example.com/securityRealm/finishLogin
  &response_type=code
  &scope=user:info user:check-access
  &state=Y2MzNTQ4ZjYtMDY2ZC00
```

As you can see that URL exactly follows OAuth workflow. Let's imagine that we would like make our
Jenkins instance be available under a different hostname, e.g. `jenkins.example.org`. First of all
we need to create a new Route that has `jenkins.example.org` in the `host` field:

```yaml
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: jenkins-example-org
spec:
  host: jenkins.example.org
  to:
    kind: Service
    name: jenkins
    weight: 100
  port:
    targetPort: web
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
```

Then you should add a CNAME record into `example.org` domain that points to Router Canonical
Hostname. If you try to open `https://jenkins.example.org` OpenShift OAuth proxy returns status code
400 with a message about invalid request. But pay attention which URL was requested. It's completely
the same URL with the same parameters including `redirect_uri`. So what should we do in order to fix
that? Jenkins template uses a Service Account as an OAuth client. The documentation says that the
Service Account should have an annotation with a key that starts with one of the following prefixes:

* `serviceaccounts.openshift.io/oauth-redirecturi`.
* `serviceaccounts.openshift.io/oauth-redirectreference`.

Let's check what we have in the Service Account for our Jenkins instance:

```yaml
kind: ServiceAccount
apiVersion: v1
metadata:
  annotations:
    serviceaccounts.openshift.io/oauth-redirectreference.jenkins: >-
      {"kind":"OAuthRedirectReference","apiVersion":"v1","reference":{"kind":"Route","name":"jenkins"}}
  name: jenkins
...
```

Thus we just need to replace the reference name of the Route. Resulting annotation should look like:
`{"kind":"OAuthRedirectReference","apiVersion":"v1","reference":{"kind":"Route","name":"jenkins-example-org"}}`.
After that authentication will work on the new URL.

## References

* <https://tools.ietf.org/html/rfc6749>
* <https://docs.openshift.com/container-platform/4.6/authentication/using-service-accounts-as-oauth-client.html>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/5)
