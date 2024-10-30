import os
import os.path
import random
import string
import tempfile
from typing import Iterator
import pytest
import docker_container_proxy
from docker_container_proxy import Generator

# pylint: disable=redefined-outer-name; (for pytest fixtures)


@pytest.fixture
def path_prefix() -> Iterator[str]:
    fixture_base_path = os.path.join(
        tempfile.gettempdir(),
        docker_container_proxy.__name__ + "." + __name__,
    )
    fixture_path = os.path.join(
        fixture_base_path,
        "".join(random.choices(string.ascii_letters + string.digits, k=6)),
    )
    yield fixture_path
    if os.path.exists(fixture_path):
        output_files = list(os.scandir(fixture_path))
        if len(output_files) == 1 and output_files[0].is_file():
            os.unlink(output_files[0].path)
        else:
            raise RuntimeError("unable to clean up after test")
        os.rmdir(fixture_path)
    if os.path.exists(fixture_base_path):
        os.rmdir(fixture_base_path)


def test_write_config_path(path_prefix: str) -> None:
    generator = Generator(name="FooBar 2.0", path_prefix=path_prefix)
    config_filename = generator.write("")
    assert config_filename.startswith(path_prefix)


def test_write_config_contents(path_prefix: str) -> None:
    generator = Generator(name="FooBar 2.0", path_prefix=path_prefix)
    config_filename = generator.write("verify me")
    with open(config_filename, "rb") as config_file:
        config_contents = config_file.read()
    assert config_contents == b"# configuration generated automatically by FooBar 2.0\n\nverify me"
