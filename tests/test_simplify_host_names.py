from typing import List
import pytest
from docker_container_proxy import simplify_host_names


@pytest.mark.parametrize(
    "input_names,expected_simplified_names",
    [
        pytest.param(
            ["foo", "bar"],
            ["foo", "bar"],
            id="nothing to simplify",
        ),
        pytest.param(
            ["foo-2", "bar-55", "baz-3"],
            ["foo", "bar", "baz"],
            id="remove numbers",
        ),
        pytest.param(
            ["qux", "qux-222"],
            ["qux", "qux-222"],
            id="number can't be removed",
        ),
        pytest.param(
            ["foo-1", "foo-2"],
            ["foo-1", "foo-2"],
            id="numbers can't be removed",
        ),
        pytest.param(
            ["alpha-nginx", "beta-nginx", "gamma-nginx"],
            ["alpha", "beta", "gamma"],
            id="remove nginx suffix",
        ),
        pytest.param(
            ["thud-nginx", "thud"],
            ["thud-nginx", "thud"],
            id="nginx suffix can't be removed",
        ),
        pytest.param(
            ["spam-nginx-1", "ham-nginx-1", "eggs-nginx-700"],
            ["spam", "ham", "eggs"],
            id="remove both numbers and nginx suffix",
        ),
        pytest.param(
            ["x-1-nginx", "y-2-nginx"],
            ["x-1", "y-2"],
            id="don't remove numbers preceeding the nginx suffix",
        ),
    ]
)
def test_simplify_host_names(input_names: str, expected_simplified_names: List[str]) -> None:
    simplified_names = simplify_host_names(input_names)
    assert list(simplified_names) == expected_simplified_names
