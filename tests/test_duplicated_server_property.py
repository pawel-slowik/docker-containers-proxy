from typing import Iterable
import pytest
from docker_container_proxy import DockerContainer, Server, HTTPProxyServer, DashboardServer
from docker_container_proxy import find_duplicated_server_property


def test_no_duplicate() -> None:
    proxies = (
        HTTPProxyServer(
            host_name="h",
            domain="d",
            listen=1,
            proxied_host="p",
            proxied_port=2,
            docker_container=DockerContainer(name="c", ports=()),
        ),
        HTTPProxyServer(
            host_name="j",
            domain="d",
            listen=1,
            proxied_host="p",
            proxied_port=3,
            docker_container=DockerContainer(name="c", ports=()),
        ),
    )
    dashboard = DashboardServer(
        host_name="k",
        domain="d",
        listen=1,
        proxy_servers=proxies,
    )
    duplicate = find_duplicated_server_property(proxies + (dashboard, ))
    assert duplicate is None


@pytest.mark.parametrize(
    "servers,expected_duplicate_reason",
    [
        (
            [
                HTTPProxyServer(
                    host_name="h",
                    domain="d",
                    listen=1,
                    proxied_host="p",
                    proxied_port=2,
                    docker_container=DockerContainer(name="j", ports=()),
                ),
                HTTPProxyServer(
                    host_name="h",
                    domain="d",
                    listen=5,
                    proxied_host="q",
                    proxied_port=7,
                    docker_container=DockerContainer(name="l", ports=()),
                ),
            ],
            "server name h.d",
        ),
        (
            [
                HTTPProxyServer(
                    host_name="h",
                    domain="d",
                    listen=1,
                    proxied_host="p",
                    proxied_port=2,
                    docker_container=DockerContainer(name="j", ports=()),
                ),
                HTTPProxyServer(
                    host_name="g",
                    domain="b",
                    listen=5,
                    proxied_host="q",
                    proxied_port=2,
                    docker_container=DockerContainer(name="l", ports=()),
                ),
            ],
            "proxied port 2",
        ),
        (
            [
                HTTPProxyServer(
                    host_name="h",
                    domain="d",
                    listen=1,
                    proxied_host="p",
                    proxied_port=2,
                    docker_container=DockerContainer(name="j", ports=()),
                ),
                DashboardServer(
                    host_name="h",
                    domain="d",
                    listen=5,
                    proxy_servers=(),
                ),
            ],
            "server name h.d",
        ),
    ]
)
def test_duplicate(servers: Iterable[Server], expected_duplicate_reason: str) -> None:
    duplicate = find_duplicated_server_property(servers)
    assert duplicate is not None
    assert duplicate.reason == expected_duplicate_reason
