import pytest
from docker_container_proxy import PortConflictError, DockerContainer, HTTPProxy
from docker_container_proxy import HTTPProxyServer, DashboardServer


def test_multiple_container_names() -> None:
    with pytest.raises(ValueError):
        DockerContainer(name="foo bar", ports=())


def test_server_port_conflict() -> None:
    with pytest.raises(PortConflictError):
        HTTPProxyServer(
            host_name="www",
            domain="example.com",
            listen=8080,
            proxied_host="localhost",
            proxied_port=8080,
            docker_container=DockerContainer(name="x", ports=()),
        )


def test_proxy_without_servers() -> None:
    dashboard_server = DashboardServer(
        host_name="_dashboard",
        domain="example.com",
        listen=80,
        proxy_servers=(),
    )
    with pytest.raises(ValueError):
        HTTPProxy(
            pid_file="foo.pid",
            access_log_file="access.log",
            error_log_file="error.log",
            listen=80,
            proxy_servers=(),
            dashboard_server=dashboard_server,
        )


def test_proxy_with_conflicting_servers() -> None:
    proxy_servers = (
        HTTPProxyServer(
            host_name="www",
            domain="example.com",
            listen=8080,
            proxied_host="localhost",
            proxied_port=80,
            docker_container=DockerContainer(name="x", ports=()),
        ),
        HTTPProxyServer(
            host_name="blog",
            domain="example.org",
            listen=8081,
            proxied_host="127.0.0.1",
            proxied_port=80,
            docker_container=DockerContainer(name="y", ports=()),
        ),
    )
    dashboard_server = DashboardServer(
        host_name="_dashboard",
        domain="example.com",
        listen=8082,
        proxy_servers=proxy_servers,
    )
    with pytest.raises(ValueError):
        HTTPProxy(
            pid_file="foo.pid",
            access_log_file="access.log",
            error_log_file="error.log",
            listen=80,
            proxy_servers=proxy_servers,
            dashboard_server=dashboard_server,
        )
