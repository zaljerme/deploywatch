import asyncio
import socket

import pytest
from aiohttp import web

from app import probe as module
from app.config import Settings
from app.probe import UnsafeDestination, probe, resolve_destination
from app.schemas import MonitorInput


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "::1",
        "::ffff:8.8.8.8",
        "192.168.0.1",
        "100.64.0.1",
    ],
)
async def test_private_destinations_blocked(monkeypatch, address):
    async def lookup(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 80))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
    with pytest.raises(UnsafeDestination):
        await resolve_destination("http://example.com", Settings())


async def test_mixed_dns_answers_blocked(monkeypatch):
    async def lookup(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 80)) for ip in ["8.8.8.8", "127.0.0.1"]
        ]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", lookup)
    with pytest.raises(UnsafeDestination):
        await resolve_destination("http://example.com", Settings())


def test_demo_exception_cannot_be_enabled_in_production():
    with pytest.raises(ValueError):
        Settings(environment="production", allow_demo=True, api_token="x" * 40)


@pytest.mark.parametrize(
    "url",
    [
        "http://user:pass@example.com",
        "http://example.com:22",
        "http://example.com/#secret",
        "http://exam\nple.com",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        MonitorInput(name="API", url=url)


async def test_probe_timeout_redirect_and_body_limit(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(request.path)
        if request.path == "/slow":
            await asyncio.sleep(0.2)
        if request.path == "/redirect":
            raise web.HTTPFound("/private")
        return web.Response(body=b"x" * (70000 if request.path == "/large" else 1))

    server = web.Application()
    server.router.add_get("/{path:.*}", handler)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    async def test_resolver(url, config):
        return ["127.0.0.1"], port

    monkeypatch.setattr(module, "resolve_destination", test_resolver)
    try:
        base = f"http://127.0.0.1:{port}"
        assert (await probe(base + "/ok", 200, 1, Settings())).success
        assert (await probe(base + "/redirect", 200, 1, Settings())).error == "redirect_blocked"
        assert "/private" not in calls
        assert (await probe(base + "/large", 200, 1, Settings())).error == "response_too_large"
        assert (await probe(base + "/slow", 200, 0.05, Settings())).error == "timeout"
    finally:
        await runner.cleanup()
