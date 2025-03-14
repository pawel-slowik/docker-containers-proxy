import xml.etree.ElementTree as et
from typing import Optional
from docker_container_proxy import DockerContainer
from docker_container_proxy import HTTPProxyServer, DashboardServer, HTTPProxy


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


def test_dashboard_server_config() -> None:
    proxy_servers = (
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
    dashboard_server = DashboardServer(
        host_name="_dashboard",
        domain="example.com",
        listen=80,
        proxy_servers=proxy_servers,
    )
    template = """\
server {
    listen 80;
    server_name _dashboard.example.com;
    location / {
        add_header Content-Type text/html;
        return 200 '$';
    }
}
"""
    begin, _, end = template.partition("$")

    config = dashboard_server.config()
    html = config[len(begin):-len(end)]

    assert config.startswith(begin)
    assert config.endswith(end)
    assert "'" not in html

    assert xpath_tag(html, ".") == "html"
    assert xpath_count(html, "./head/title") == 1
    assert xpath_count(html, "./body/table") == 1
    assert xpath_count(html, "./body/table/thead/tr") == 1
    assert xpath_count(html, "./body/table/tbody/tr") == 2

    assert xpath_text(html, "./head/title") == "hosts proxied for Docker containers"
    assert xpath_text(html, "./body/table/caption") == "hosts proxied for Docker containers"
    assert xpath_text(html, "./body/table/thead/tr/th[1]") == "host"
    assert xpath_text(html, "./body/table/thead/tr/th[2]") == "Docker container"
    assert xpath_text(html, "./body/table/thead/tr/th[3]") == "URL"

    assert xpath_text(html, "./body/table/tbody/tr[1]/td[1]/a") == "www"
    assert xpath_href(html, "./body/table/tbody/tr[1]/td[1]/a") == proxy_servers[0].url
    assert xpath_text(html, "./body/table/tbody/tr[1]/td[2]/a") == "www-backend"
    assert xpath_href(html, "./body/table/tbody/tr[1]/td[2]/a") == proxy_servers[0].url
    assert xpath_text(html, "./body/table/tbody/tr[1]/td[3]/a") == proxy_servers[0].url
    assert xpath_href(html, "./body/table/tbody/tr[1]/td[3]/a") == proxy_servers[0].url

    assert xpath_text(html, "./body/table/tbody/tr[2]/td[1]/a") == "blog"
    assert xpath_href(html, "./body/table/tbody/tr[2]/td[1]/a") == proxy_servers[1].url
    assert xpath_text(html, "./body/table/tbody/tr[2]/td[2]/a") == "blog-backend"
    assert xpath_href(html, "./body/table/tbody/tr[2]/td[1]/a") == proxy_servers[1].url
    assert xpath_text(html, "./body/table/tbody/tr[2]/td[3]/a") == proxy_servers[1].url
    assert xpath_href(html, "./body/table/tbody/tr[2]/td[1]/a") == proxy_servers[1].url


def test_proxy_config() -> None:
    proxy_servers = (
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
    dashboard_server = DashboardServer(
        host_name="_dashboard",
        domain="example.com",
        listen=80,
        proxy_servers=proxy_servers,
    )

    # mocker.patch.object doesn't work on frozen dataclasses
    object.__setattr__(proxy_servers[0], "config", lambda: "---- FIRST PROXY CONFIG HERE ----")
    object.__setattr__(proxy_servers[1], "config", lambda: "---- SECOND PROXY CONFIG HERE ----")
    object.__setattr__(dashboard_server, "config", lambda: "---- DASHBOARD CONFIG HERE ----")

    proxy = HTTPProxy(
        pid_file="/run/nginx.pid",
        error_log_file="/var/log/nginx/error.log",
        access_log_file="/var/log/nginx/access.log",
        listen=80,
        servers=(dashboard_server, ) + proxy_servers,
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

    ---- DASHBOARD CONFIG HERE ----
    ---- FIRST PROXY CONFIG HERE ----
    ---- SECOND PROXY CONFIG HERE ----
}
"""


def xpath_tag(html: str, xpath: str) -> Optional[str]:
    element = et.fromstring(html).find(xpath)
    return None if element is None else element.tag


def xpath_text(html: str, xpath: str) -> Optional[str]:
    element = et.fromstring(html).find(xpath)
    return None if element is None else element.text


def xpath_href(html: str, xpath: str) -> Optional[str]:
    element = et.fromstring(html).find(xpath)
    return None if element is None else element.attrib["href"]


def xpath_count(html: str, xpath: str) -> int:
    return len(et.fromstring(html).findall(xpath))
