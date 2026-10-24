import asyncio
import ipaddress
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver

from app.config import Settings

MAX_BODY = 65536


class UnsafeDestination(ValueError):
    pass


def is_public_address(address: str):
    ip = ipaddress.ip_address(address)
    if not ip.is_global or "%" in address:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        # Transition mechanisms can embed a private IPv4 destination in a global IPv6 address.
        if ip.ipv4_mapped or ip.sixtofour or ip.teredo:
            return False
        if any(
            ip in network
            for network in (
                ipaddress.ip_network("64:ff9b::/96"),
                ipaddress.ip_network("64:ff9b:1::/48"),
            )
        ):
            return False
    return True


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    status_code: int | None
    response_ms: int
    error: str | None = None


async def resolve_destination(url: str, config: Settings):
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    demo = (
        config.environment == "development"
        and config.allow_demo
        and url == f"http://{config.demo_host}:8001/health"
    )
    if port not in {80, 443} and not demo:
        raise UnsafeDestination("port is not allowed")
    records = await asyncio.get_running_loop().getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    addresses = sorted({record[4][0] for record in records})
    if not addresses or (not demo and any(not is_public_address(address) for address in addresses)):
        raise UnsafeDestination("destination must resolve exclusively to public addresses")
    return addresses, port


class PinnedResolver(AbstractResolver):
    def __init__(self, addresses):
        self.addresses = addresses

    async def resolve(self, host, port=0, family=socket.AF_INET):
        return [
            dict(
                hostname=host,
                host=address,
                port=port,
                family=socket.AF_INET6 if ":" in address else socket.AF_INET,
                proto=0,
                flags=socket.AI_NUMERICHOST,
            )
            for address in self.addresses
        ]

    async def close(self):
        pass


async def probe(url: str, expected_status: int, timeout: int, config: Settings):
    started = time.monotonic()
    status = None
    error = None
    try:
        # The outer deadline includes DNS; the connector uses only the validated snapshot.
        async with asyncio.timeout(timeout):
            addresses, _ = await resolve_destination(url, config)
            connector = aiohttp.TCPConnector(
                resolver=PinnedResolver(addresses), use_dns_cache=False
            )
            async with aiohttp.ClientSession(
                connector=connector,
                trust_env=False,
                auto_decompress=False,
                timeout=aiohttp.ClientTimeout(total=timeout),
                max_line_size=8190,
                max_field_size=8190,
            ) as client:
                async with client.get(url, allow_redirects=False) as response:
                    status = response.status
                    size = 0
                    async for chunk in response.content.iter_chunked(8192):
                        size += len(chunk)
                        if size > MAX_BODY:
                            error = "response_too_large"
                            break
                    if 300 <= status < 400:
                        error = "redirect_blocked"
                    elif status != expected_status:
                        error = "unexpected_status"
    except TimeoutError:
        error = "timeout"
    except UnsafeDestination:
        error = "unsafe_destination"
    except (aiohttp.ClientError, OSError, ValueError):
        error = "network_error"
    return ProbeResult(error is None, status, round((time.monotonic() - started) * 1000), error)
