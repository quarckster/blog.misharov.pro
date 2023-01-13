---
title: MockServer
tags: mocking, rest, testing
---
In unit testing we often mock various objects, libraries and side effects. For example it can be a
response from some web service. But what should we do in integration and functional tests?

## The problem

Let's imagine that your application receives  data from a third-party web service and you want to
run integration tests. Running tests against the real web service is not the best idea. You probably
need to provide credentials and maybe other sensitive data that doesn't make sense to pass into a
testing environment. A good approach would be set up a fake web server that can emulate behavior
of the real third-party service.

## The solution

I found an interesting piece of software called `MockServer`. Let me quote the description from the
official site:

>For any system you integrate with via HTTP or HTTPS MockServer can be used as:
>
>* a mock configured to return specific responses for different requests
>* a proxy recording and optionally modifying requests and responses
>* both a proxy for some requests and a mock for other requests at the same time
>
>When MockServer receives a request it matches the request against active expectations that have
>been configured, if no matches are found it proxies the request if appropriate otherwise a 404 is
>returned.
>
>For each request received the following steps happen:
>
>* find matching expectation and perform action
>* if no matching expectation proxy request
>* if not a proxy request return 404

Sounds pretty cool. Let me share how I used it in one of my pet projects.

## Usage

In order to start using `MockServer` you should define which endpoints you would like to mock.
Perhaps you will need to modify the code of your application to have the ability to configure a
proxy server. Then you need to record requests and responses using built-in proxy of `MockServer`.
Just run the server:

```sh
java -jar mockserver-netty-5.11.2-jar-with-dependencies.jar -serverPort 8080
```

And configure system proxy to `http://localhost:8080/`. Send some requests via proxy and then you
can download recorded requests and responses via `MockServer` REST API:

```sh
curl -X PUT "http://localhost:8080/mockserver/retrieve?type=REQUEST_RESPONSES"
```

The output is just a json with the following structure:

```json
[
  {
    "httpRequest": {
      "method": "GET",
      "path": "/some/endpoint"
    },
    "httpResponse": {
      "statusCode": 200,
      "reasonPhrase": "OK",
      "body": {
        "status": 200,
        ...
        }
      }
    }
  },
  ...
]
```

The replay contains a lot of request and responses aspects such as cookies, various headers and so
on. You might not need to store all of them therefore feel free to edit the file to keep only
required data. After that you can use this file in your tests. Run the `MockServer` and specify
the path to the replay file:

```sh
export MOCKSERVER_INITIALIZATION_JSON_PATH=<path to replay file>
java -jar mockserver-netty-5.11.2-jar-with-dependencies.jar -serverPort 8080
```

When your application sends a request to the third-party web service via `MockServer` proxy it will
get exactly the same responses that you specified in `httpResponse` stanzas.

### HTTPS & TLS

Nowadays almost all web applications work only wih HTTPS. It means that you cannot intercept traffic
between the client and the server. `MockServer` is able to mock the behaviour of multiple hostnames
and present a valid X.509 Certificates for them. `MockServer` achieves this by dynamically
generating its X.509 Certificate using an in-memory list of hostnames and ip addresses. Create a
`mockserver.properties` file with the following content:

```txt
###############################
# MockServer & Proxy Settings #
###############################

# Certificate Generation

# dynamically generated CA key pair (if they don't already exist in specified directory)
mockserver.dynamicallyCreateCertificateAuthorityCertificate=true
# save dynamically generated CA key pair in working directory
mockserver.directoryToSaveDynamicSSLCertificate=.
# certificate domain name (default "localhost")
mockserver.sslCertificateDomainName=localhost
# comma separated list of ip addresses for Subject Alternative Name domain names (default empty list)
mockserver.sslSubjectAlternativeNameDomains=<third-party web service host name>
```

Run the `MockServer`:

```sh
export MOCKSERVER_PROPERTY_FILE=mockserver.properties
java -jar mockserver-netty-5.11.2-jar-with-dependencies.jar -serverPort 8080
```

And after that you will find two new files: `CertificateAuthorityCertificate.pem` and
`PKCS8CertificateAuthorityPrivateKey.pem`. We should add MockServer's CA into the system list of
trusted Certificate Authorities. The following commands are applicable for Ubuntu:

```sh
sudo cp CertificateAuthorityCertificate.pem /usr/local/share/ca-certificates/MockServer.crt
sudo update-ca-certificates
```

WARNING! Remember if you add a new Certificate Authority into your system the issuer can listen to
your traffic. Do not install random CAs from the internet!

In case of `MockServer` it's safe because you are the issuer :).

After these procedures `MockServer` will be able to record requests and responses to any HTTPS
resource.

## Conclusion

`MockServer` is a powerful tool that gives unlimited ability for creating fake APIs of any web
service. I described a small amount of its features and abilities because `MockServer` really can do
a lot. More details you will find in very good documentation on the official site.

References:

* <https://mock-server.com/>

[Discuss on Github](https://github.com/quarckster/blog.misharov.pro/discussions/12)
