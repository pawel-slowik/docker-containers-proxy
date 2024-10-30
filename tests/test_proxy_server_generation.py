from typing import Optional
import pytest
from docker_container_proxy import IPVersion, BaseProxyConfig, DockerContainer, PortConflictError
from docker_container_proxy import generate_proxies


def test_properties() -> None:
    container = create_container_stub(name="a-rose", exposed_port=1337)
    config = BaseProxyConfig(listen=8080, proxy_host="10.0.0.30", domain="invalid")

    servers = list(generate_proxies((container,), 80, IPVersion.V4, config))

    assert len(servers) == 1
    assert servers[0].host_name == "a-rose"
    assert servers[0].domain == "invalid"
    assert servers[0].listen == 8080
    assert servers[0].proxied_host == "10.0.0.30"
    assert servers[0].proxied_port == 1337
    assert servers[0].docker_container == container


def test_skips_containers_without_exposed_port() -> None:
    containers = (
        create_container_stub(name="pick-me", exposed_port=5),
        create_container_stub(name="keep-me-out-of-this", exposed_port=None),
        create_container_stub(name="pick-me-too", exposed_port=80),
    )
    config = BaseProxyConfig(listen=8080, proxy_host="10.0.1.40", domain="test")

    servers = list(generate_proxies(containers, 80, IPVersion.V4, config))

    assert len(servers) == 2
    assert servers[0].host_name == "pick-me"
    assert servers[0].docker_container == containers[0]
    assert servers[1].host_name == "pick-me-too"
    assert servers[1].docker_container == containers[2]


def test_errors_on_port_conflict() -> None:
    container = create_container_stub(name="foobar", exposed_port=8080)
    config = BaseProxyConfig(listen=8080, proxy_host="10.0.2.50", domain="example")
    with pytest.raises(PortConflictError):
        list(generate_proxies((container,), 80, IPVersion.V4, config))


def create_container_stub(name: str, exposed_port: Optional[int]) -> DockerContainer:
    container = DockerContainer(name=name, ports=())
    # mocker.patch.object doesn't work on frozen dataclasses
    object.__setattr__(
        container,
        "pick_exposed_port",
        lambda internal_port, ip_version: exposed_port,
    )
    return container
