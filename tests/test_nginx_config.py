from docker_container_proxy import DockerContainer
from docker_container_proxy import HTTPProxyServer, HTTPProxy


def test_proxy_server_config() -> None:
    server = HTTPProxyServer(
        host_name="www",
        domain="example.com",
        listen=80,
        proxied_host="192.168.0.10",
        proxied_port=8080,
        docker_container=DockerContainer(name="www-backend", ports=()),
    )
    assert server.config() == """\
server {
    listen 80;
    server_name www.example.com;
    location / {
        proxy_pass http://192.168.0.10:8080;
    }
}
"""


def test_proxy_config() -> None:
    servers = (
        HTTPProxyServer(
            host_name="www",
            domain="example.com",
            listen=80,
            proxied_host="192.168.0.10",
            proxied_port=8080,
            docker_container=DockerContainer(name="www-backend", ports=()),
        ),
        HTTPProxyServer(
            host_name="blog",
            domain="example.com",
            listen=80,
            proxied_host="192.168.0.10",
            proxied_port=8081,
            docker_container=DockerContainer(name="blog-backend", ports=()),
        ),
    )
    proxy = HTTPProxy(
        pid_file="/run/nginx.pid",
        error_log_file="/var/log/nginx/error.log",
        access_log_file="/var/log/nginx/access.log",
        listen=80,
        servers=servers,
    )
    assert proxy.config() == """\
pid /run/nginx.pid;
error_log /var/log/nginx/error.log;

events { }

http {
    access_log /var/log/nginx/access.log;

    server {
        listen 80 default_server;
        server_name _;
        return 400;
    }

    server {
        listen 80;
        server_name www.example.com;
        location / {
            proxy_pass http://192.168.0.10:8080;
        }
    }

    server {
        listen 80;
        server_name blog.example.com;
        location / {
            proxy_pass http://192.168.0.10:8081;
        }
    }
}
"""
