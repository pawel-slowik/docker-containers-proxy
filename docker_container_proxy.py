#!/usr/bin/env python3

from __future__ import annotations
import dataclasses
import enum
import json
import os
import os.path
import re
import string
import subprocess
import sys
import textwrap
import argparse
from typing import Iterable, Optional


@enum.unique
class IPVersion(enum.Enum):
    V4 = 4
    V6 = 6


@dataclasses.dataclass(frozen=True)
class PortMapping:
    exposed: int
    internal: int
    ip_version: IPVersion


@dataclasses.dataclass(frozen=True)
class DockerContainer:
    name: str
    ports: tuple[PortMapping, ...]

    def __post_init__(self) -> None:
        # multiple names and fancy characters not supported because that would
        # require special handling when generating nginx configuration
        if not re.fullmatch(r"^[-_a-z0-9]+$", self.name):
            raise ValueError(f"unsupported characters in container name: {self.name}")

    def pick_exposed_port(self, internal_port: int, ip_version: IPVersion) -> Optional[int]:
        port_mappings = tuple(filter(
            lambda pm: pm.internal == internal_port and pm.ip_version == ip_version,
            self.ports,
        ))
        return port_mappings[0].exposed if len(port_mappings) == 1 else None


def list_containers() -> Iterable[DockerContainer]:
    process = subprocess.run(["docker", "ps", "--format=json"], capture_output=True, check=True)
    return parse_containers(process.stdout)


def parse_containers(docker_ps_output: bytes) -> Iterable[DockerContainer]:
    for line in docker_ps_output.splitlines():
        data = json.loads(line)
        yield DockerContainer(
            name=data["Names"],
            ports=tuple(parse_port_mappings(data["Ports"])),
        )


def parse_port_mappings(ports: str) -> Iterable[PortMapping]:
    chunks = [chunk.strip() for chunk in ports.split(",")]
    for chunk in chunks:
        if chunk.count("/") != 1:
            continue
        address, protocol = chunk.split("/")
        if protocol != "tcp":
            continue
        if address.count("->") != 1:
            continue
        source, destination = address.split("->")
        search = re.search(r"([0-9]+)$", source)
        if not search:
            continue
        exposed = int(search.group(1))
        search = re.search(r"([0-9]+)$", destination)
        if not search:
            continue
        internal = int(search.group(1))
        # inaccurate, but good enough for now
        ip_version = IPVersion.V6 if "::" in source or "::" in destination else IPVersion.V4
        yield PortMapping(exposed=exposed, internal=internal, ip_version=ip_version)


class PortConflictError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class HTTPProxyServer:
    host_name: str
    domain: str
    listen: int
    proxied_host: str
    proxied_port: int
    docker_container: DockerContainer

    def __post_init__(self) -> None:
        if self.proxied_port == self.listen:
            raise PortConflictError(
                f"proxy with server name {self.server_name}"
                f" can't listen on port {self.listen} because it conflicts with the proxied port"
            )

    @property
    def server_name(self) -> str:
        return self.host_name + "." + self.domain

    @property
    def url(self) -> str:
        return f"http://{self.server_name}:{self.listen}/"

    def config(self) -> str:
        template = string.Template("""\
server {
    listen $listen;
    server_name $server_name;
    location / {
        proxy_pass http://$proxied_host:$proxied_port;
    }
}
""")
        return template.substitute(dataclasses.asdict(self), server_name=self.server_name)


@dataclasses.dataclass(frozen=True)
class BaseProxyConfig:
    listen: int
    proxy_host: str
    domain: str

    @staticmethod
    def from_cli_args(args: argparse.Namespace) -> BaseProxyConfig:
        return BaseProxyConfig(
            listen=int(args.port),
            proxy_host=args.host,
            domain=args.domain,
        )


def generate_proxies(
    containers: Iterable[DockerContainer],
    container_internal_port: int,
    ip_version: IPVersion,
    base_config: BaseProxyConfig,
) -> Iterable[HTTPProxyServer]:
    for container in containers:
        exposed_port = container.pick_exposed_port(container_internal_port, ip_version)
        if exposed_port is None:
            continue
        try:
            server = HTTPProxyServer(
                host_name=container.name,
                domain=base_config.domain,
                listen=base_config.listen,
                proxied_host=base_config.proxy_host,
                proxied_port=exposed_port,
                docker_container=container,
            )
        except PortConflictError as port_conflict_error:
            raise PortConflictError(
                f"port {exposed_port} exposed by container {container.name}"
                " conflicts with proxy configuration"
            ) from port_conflict_error
        yield server


@dataclasses.dataclass(frozen=True)
class Duplicate:
    reason: str
    container: DockerContainer
    another_container: DockerContainer


def check_uniqueness(proxies: Iterable[HTTPProxyServer]) -> None:
    duplicate = find_duplicated_proxy_property(proxies)
    if not duplicate:
        return
    raise ValueError(
        f"duplicated {duplicate.reason}, used both by docker container"
        f" {duplicate.container.name} and by {duplicate.another_container.name}"
    )


def find_duplicated_proxy_property(proxies: Iterable[HTTPProxyServer]) -> Optional[Duplicate]:

    def compare(proxy: HTTPProxyServer, another_proxy: HTTPProxyServer) -> Optional[str]:
        if proxy.server_name == another_proxy.server_name:
            return f"server name {proxy.server_name}"
        if proxy.proxied_port == another_proxy.proxied_port:
            return f"proxied port {proxy.proxied_port}"
        return None

    proxies = tuple(proxies)
    for index, proxy in enumerate(proxies):
        for another_index, another_proxy in enumerate(proxies):
            if index == another_index:
                continue
            reason = compare(proxy, another_proxy)
            if reason is not None:
                return Duplicate(
                    reason=reason,
                    container=proxy.docker_container,
                    another_container=another_proxy.docker_container,
                )
    return None


def simplify_proxy_host_names(proxies: Iterable[HTTPProxyServer]) -> Iterable[HTTPProxyServer]:
    proxies = tuple(proxies)
    simplified_host_names = tuple(simplify_host_names([proxy.host_name for proxy in proxies]))
    for proxy, simplified_host_name in zip(proxies, simplified_host_names, strict=True):
        yield dataclasses.replace(proxy, host_name=simplified_host_name)


def simplify_host_names(names: Iterable[str]) -> Iterable[str]:

    def strip_number_suffix(name: str) -> str:
        match = re.fullmatch(r"^(.*)-[0-9]+$", name)
        return match.group(1) if match else name

    def strip_nginx_suffix(name: str) -> str:
        return name[:-6] if name.endswith("-nginx") else name

    names = tuple(names)
    for func in (strip_number_suffix, strip_nginx_suffix,):
        stripped_names = tuple(map(func, names))
        if len(set(stripped_names)) == len(names):
            names = stripped_names
    return names


@dataclasses.dataclass(frozen=True)
class HTTPProxy:
    pid_file: str
    error_log_file: str
    access_log_file: str
    listen: int
    servers: tuple[HTTPProxyServer, ...]

    def __post_init__(self) -> None:
        if not self.servers:
            raise ValueError("no servers to set up")
        check_uniqueness(self.servers)

    @staticmethod
    def from_config_generator(
        base_confg: BaseProxyConfig,
        generator: Generator,
        servers: Iterable[HTTPProxyServer],
    ) -> HTTPProxy:
        return HTTPProxy(
            pid_file=os.path.join(generator.path_prefix, "nginx.pid"),
            error_log_file=os.path.join(generator.path_prefix, "error.log"),
            access_log_file=os.path.join(generator.path_prefix, "access.log"),
            listen=base_confg.listen,
            servers=tuple(servers),
        )

    def config(self) -> str:
        template = string.Template("""\
pid $pid_file;
error_log $error_log_file;

events { }

http {
    access_log $access_log_file;

    server {
        listen $listen default_server;
        server_name _;
        return 400;
    }

    $servers
}
""")
        servers = textwrap.indent(
            "\n".join(server.config() for server in self.servers),
            "    ",
        )
        return template.substitute(dataclasses.asdict(self), servers=servers.strip())


@dataclasses.dataclass(frozen=True)
class Generator:
    name: str
    path_prefix: str

    @staticmethod
    def from_script_name() -> Generator:
        script_name = os.path.basename(sys.argv[0])
        path_prefix = os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
            os.path.splitext(script_name)[0],
        )
        return Generator(
            name=os.path.abspath(script_name),
            path_prefix=path_prefix,
        )

    def write(self, config: str) -> str:
        if not os.path.exists(self.path_prefix):
            os.makedirs(self.path_prefix, exist_ok=True)
        config_filename = os.path.join(self.path_prefix, "nginx.conf")
        with open(config_filename, "w", encoding="us-ascii") as config_file:
            config_file.write(f"# configuration generated automatically by {self.name}\n\n")
            config_file.write(config)
        return config_filename


def restart_proxy(config_filename: str, pid_filename: str) -> None:
    nginx_command = ["/usr/sbin/nginx", "-c", config_filename]
    if os.path.exists(pid_filename):
        nginx_command += ["-s", "reload"]
    subprocess.run(nginx_command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Configure and run a nginx HTTP proxy for Docker containers.",
        add_help=False,  # avoid conflict with -h host
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-p", dest="port", help="listen on port", default=8080, type=int)
    parser.add_argument("-h", dest="host", help="proxy host", default="localhost")
    parser.add_argument("-d", dest="domain", help="domain for containers", default="test")
    parser.add_argument(
        "--dry-run", dest="dry_run", action="store_true",
        help="display generated configuration without saving it"
    )
    parser.add_argument("--help", action="help", help="show this help message and exit")
    args = parser.parse_args()
    generator = Generator.from_script_name()
    base_config = BaseProxyConfig.from_cli_args(args)
    containers = list_containers()
    proxy_servers = generate_proxies(containers, 80, IPVersion.V4, base_config)
    proxy_servers = simplify_proxy_host_names(proxy_servers)
    proxy = HTTPProxy.from_config_generator(base_config, generator, proxy_servers)
    if args.dry_run:
        print(proxy.config(), end="")
    else:
        for proxy_server in proxy.servers:
            print(proxy_server.url)
        config_filename = generator.write(proxy.config())
        print(f"configuration saved to {config_filename}")
        restart_proxy(config_filename, proxy.pid_file)
        print("proxy restarted")


if __name__ == "__main__":
    main()
