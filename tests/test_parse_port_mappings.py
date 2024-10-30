from typing import List
import pytest
from docker_container_proxy import IPVersion, PortMapping, parse_port_mappings


@pytest.mark.parametrize(
    "input_ports,expected_parsed_ports",
    [
        pytest.param(
            "0.0.0.0:32768->80/tcp, :::32767->79/tcp",
            [
                PortMapping(exposed=32768, internal=80, ip_version=IPVersion.V4),
                PortMapping(exposed=32767, internal=79, ip_version=IPVersion.V6),
            ],
            id="both IPv4 and IPv6",
        ),
        pytest.param(
            "0.0.0.0:8082->81/tcp",
            [
                PortMapping(exposed=8082, internal=81, ip_version=IPVersion.V4),
            ],
            id="IPv4 only",
        ),
        pytest.param(
            ":::8080->10080/tcp",
            [
                PortMapping(exposed=8080, internal=10080, ip_version=IPVersion.V6),
            ],
            id="IPv6 only",
        ),
        pytest.param(
            "9000/tcp",
            [],
            id="not exposed",
        ),
        pytest.param(
            "0.0.0.0:8082->81/nnn",
            [],
            id="not TCP",
        ),
    ]
)
def test_port_mapping_parsing(input_ports: str, expected_parsed_ports: List[PortMapping]) -> None:
    parsed_ports = parse_port_mappings(input_ports)
    assert list(parsed_ports) == expected_parsed_ports
