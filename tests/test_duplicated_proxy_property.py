from typing import Iterable
import pytest
from docker_container_proxy import DockerContainer, HTTPProxyServer
from docker_container_proxy import find_duplicated_proxy_property


Proxy = HTTPProxyServer
Container = DockerContainer


def test_no_duplicate() -> None:
    proxies = [
        Proxy(
            host_name="h",
            domain="d",
            listen=1,
            proxied_host="p",
            proxied_port=2,
            docker_container=DockerContainer(name="c", ports=()),
        ),
        Proxy(
            host_name="j",
            domain="d",
            listen=1,
            proxied_host="p",
            proxied_port=3,
            docker_container=DockerContainer(name="c", ports=()),
        ),
    ]
    duplicate = find_duplicated_proxy_property(proxies)
    assert duplicate is None


@pytest.mark.parametrize(
    "proxies,expected_duplicate_reason",
    [
        (
            [
                Proxy(
                    host_name="h",
                    domain="d",
                    listen=1,
                    proxied_host="p",
                    proxied_port=2,
                    docker_container=DockerContainer(name="j", ports=()),
                ),
                Proxy(
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
                Proxy(
                    host_name="h",
                    domain="d",
                    listen=1,
                    proxied_host="p",
                    proxied_port=2,
                    docker_container=DockerContainer(name="j", ports=()),
                ),
                Proxy(
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
    ]
)
def test_duplicate(proxies: Iterable[HTTPProxyServer], expected_duplicate_reason: str) -> None:
    duplicate = find_duplicated_proxy_property(proxies)
    assert duplicate is not None
    assert duplicate.reason == expected_duplicate_reason
