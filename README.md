![Build Status][build-badge]

[build-badge]: https://github.com/pawel-slowik/docker-containers-proxy/workflows/tests/badge.svg


# Nginx proxy for Docker containers

This script configures and starts a [nginx](https://nginx.org/) HTTP proxy for
currently running [Docker](https://www.docker.com/) containers.

It's meant to be used as a tool for exposing the HTTP service from multiple
containers, using host names instead of port numbers to distinguish between
them. It's mainly useful in a local development environment with multiple
unrelated dockerized projects. To aid in this, it provides a simple dashboard
listing the exposed containers along with their URLs.


## Usage scenario

When setting up multiple unrelated projects with docker compose, port conflicts
are pretty much unavoidable. They can be solved by customizing port numbers in a
`docker-compose.override.yml` file or via environment variables, if the project
supports them. However, this still leaves us with URLs of the form
`http://127.0.0.1:8080` for one project and `http://127.0.0.1:8081` for another,
which can be easily mixed up. The aim of this project is to replace the URLs
with something along the lines of `http://project-one.test` and
`http://another-project.test`. The included dashboard makes it easier to get an
overview of running services / projects and to pick the URL of the project we
are currently working on.


## Installation

There's no packaged version of this script. Clone this repository and call
`docker_container_proxy.py` with appropriate path.


### Requirements

The script requires Python 3.x to run. Also, since it is designed to be run on
the Docker host (not inside a container), the `docker` and `/usr/sbin/nginx`
binaries should be callable. Make sure you have installed the relevant packages
for your distribution.

The script does not require root privileges, unless you wish to bind the proxy
to a privileged port.


## Usage

Start the Docker containers for your projects first. Then, run
`/path/docker_container_proxy.py --dry-run` and verify the generated
configuration. If you wish to customize it, run `/path/docker_container_proxy.py
--help` and have a look at the available options:

    options:
      -p PORT    listen on port (default: 8080)
      -h HOST    proxy host (default: localhost)
      -d DOMAIN  domain for containers (default: test)

If you are satisfied with the result, re-run the command without the `--dry-run`
flag. This will save the generated configuration into a file and start the nginx
server. It will also print the proxied URL of each container, along with the URL
of the dashboard.

Please note that even though the generated configuration refers to proxied
containers using host names in the `-d` domain, the script does not modify your
DNS setup in any way. Therefore you'll need to alter your DNS configuration so
that the generated host names point to the IP address that the proxy is
listening on (most likely `127.0.0.1`).

You can change the location of the generated files by setting the
`XDG_DATA_HOME` environment variable.


### Example

Given the following command:

    ./docker_container_proxy.py -p 8080 -h localhost -d docker.test --dry-run

and `docker ps` output:

    CONTAINER ID   IMAGE                      COMMAND                  CREATED          STATUS          PORTS                                       NAMES
    af1da218c0ca   slim-soap-server-nginx     "/docker-entrypoint.…"   56 minutes ago   Up 56 minutes   0.0.0.0:32769->80/tcp, :::32769->80/tcp     slim-soap-server-nginx-1
    58fd11957911   slim-soap-server-php-fpm   "docker-php-entrypoi…"   57 minutes ago   Up 56 minutes   9000/tcp                                    slim-soap-server-php-fpm-1
    d0133fbafe51   districts-nginx            "/docker-entrypoint.…"   4 hours ago      Up 2 minutes    0.0.0.0:32770->80/tcp, :::32770->80/tcp     districts-nginx-1
    6150a9101dea   districts-php              "docker-php-entrypoi…"   4 hours ago      Up 2 minutes    9000/tcp                                    districts-php-fpm-1
    5437d3707dd3   phpactor                   "phpactor language-s…"   6 hours ago      Up 6 hours      0.0.0.0:4000->4000/tcp, :::4000->4000/tcp   upbeat_tharp
    85d416281770   mariadb:10.5               "docker-entrypoint.s…"   7 hours ago      Up 2 minutes    3306/tcp                                    districts-sql-1

the script will generate the following nginx configuration:

    pid /home/test/.local/share/docker_container_proxy/nginx.pid;
    error_log /home/test/.local/share/docker_container_proxy/error.log;

    events { }

    http {
        access_log /home/test/.local/share/docker_container_proxy/access.log;

        server {
            listen 8080 default_server;
            server_name _;
            return 400;
        }

        server {
            listen 8080;
            server_name _dashboard.docker.test;
            location / {
                add_header Content-Type text/html;
                return 200 '<!DOCTYPE html>some generated HTML here...</html>';
            }
        }

        server {
            listen 8080;
            server_name slim-soap-server.docker.test;
            location / {
                proxy_pass http://localhost:32769;
            }
        }

        server {
            listen 8080;
            server_name districts.docker.test;
            location / {
                proxy_pass http://localhost:32770;
            }
        }
    }

Main points worth noting:

- Only two containers have been proxied, `slim-soap-server-nginx-1` and
  `districts-nginx-1`, because they are the only ones that run a service on the
  HTTP port 80 and make it available from outside of the container.
- The names of the containers have been simplified for use in server names e.g.
  `slim-soap-server-nginx-1` to `slim-soap-server`.
- There's a catch-all / default proxy that always responds with a HTTP 400 Bad
  Request error. This is to make sure that the proxied servers only handle
  requests that are explicitly targeted at a given server.
- There's also a simple dashboard listing all the proxied containers with their
  respective URLs. It can be accessed with the `_dashboard` host name.
- As mentioned above in the section regarding DNS configuration, the generated
  host names must be made resolvable, e.g. by manually adding entries to the
  `/etc/hosts` file:

        127.0.0.1    slim-soap-server.docker.test
        127.0.0.1    districts.docker.test

After re-running the command without the `--dry-run` flag the output will
include URLs of the proxied containers:

    http://_dashboard.docker.test:8080/
    http://slim-soap-server.docker.test:8080/
    http://districts.docker.test:8080/
    configuration saved to /home/test/.local/share/docker_container_proxy/nginx.conf
    proxy restarted


## Alternatives

[Traefik](https://traefik.io/) is a popular solution that can handle this and
many more scenarios. An important difference is that Traefik is designed to be
run *inside* a container and therefore must share a Docker network with the
proxied service(s). This script does not have that requirement, but on the other
hand, since it runs *outside* of a container, the proxied service must be
exposed to the Docker host (which is not required for Traefik). Basically, this
script only handles a single use case and may be used when installing Traefik
feels like overkill.
