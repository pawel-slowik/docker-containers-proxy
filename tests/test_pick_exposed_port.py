from typing import Tuple
import pytest
from docker_container_proxy import DockerContainer, IPVersion, PortMapping


@pytest.mark.parametrize(
    "ports,internal_port,ip_version,expected_exposed_port",
    [
        pytest.param(
            (
                PortMapping(exposed=8080, internal=80, ip_version=IPVersion.V4),
                PortMapping(exposed=9999, internal=80, ip_version=IPVersion.V4),
            ),
            80,
            IPVersion.V4,
            None,
            id="multiple matches",
        ),
        pytest.param(
            (
                PortMapping(exposed=8080, internal=81, ip_version=IPVersion.V4),
            ),
            80,
            IPVersion.V4,
            None,
            id="no match on internal port",
        ),
        pytest.param(
            (
                PortMapping(exposed=8080, internal=80, ip_version=IPVersion.V6),
            ),
            80,
            IPVersion.V4,
            None,
            id="no match on IP version",
        ),
        pytest.param(
            (
                PortMapping(exposed=7777, internal=81, ip_version=IPVersion.V6),
                PortMapping(exposed=8888, internal=80, ip_version=IPVersion.V4),
                PortMapping(exposed=9999, internal=81, ip_version=IPVersion.V4),
            ),
            81,
            IPVersion.V4,
            9999,
            id="single match",
        ),
    ]
)
def test_pick_exposed_port(
    ports: Tuple[PortMapping],
    internal_port: int,
    ip_version: IPVersion,
    expected_exposed_port: int,
) -> None:
    container = DockerContainer(name="x", ports=ports)
    exposed_port = container.pick_exposed_port(internal_port, ip_version)
    assert exposed_port == expected_exposed_port
