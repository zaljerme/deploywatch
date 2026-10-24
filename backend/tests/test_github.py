import httpx
import pytest

from app.github import ActivityService


def commit(sha="abc123"):
    return {
        "sha": sha,
        "commit": {
            "message": "Fix timeout handling",
            "committer": {
                "date": "2026-01-01T00:00:00Z",
            },
        },
    }


async def test_pagination_and_commits_are_not_deployments():
    pages = []

    def handler(request):
        page = int(request.url.params["page"])
        pages.append((request.url.path, page))
        if request.url.path.endswith("deployments"):
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "abc123",
                        "created_at": "2026-01-01T00:00:00Z",
                        "environment": "staging",
                    }
                ],
            )
        return httpx.Response(
            200,
            json=[commit(f"abc{page}")],
            headers={
                "Link": '<https://evil.example/leak>; rel="next"' if page < 2 else "",
            },
        )

    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        result = await ActivityService().get("owner/repo", client)
    assert len(result["commits"]["items"]) == 2
    assert result["commits"]["items"][0]["kind"] == "commit"
    assert result["deployments"]["items"][0]["kind"] == "deployment"
    assert all(path.startswith("/repos/owner/repo/") for path, _ in pages)


@pytest.mark.parametrize("failure", [403, 429, 500, "timeout", "malformed", "large"])
async def test_failure_isolated_to_stream_and_cache_backoff(failure):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if request.url.path.endswith("deployments"):
            return httpx.Response(200, json=[])
        if failure == "timeout":
            raise httpx.ReadTimeout("test")
        if failure == "malformed":
            return httpx.Response(200, json={"bad": True})
        if failure == "large":
            return httpx.Response(200, content=b"x" * 1048577)
        return httpx.Response(failure, headers={"retry-after": "120"})

    service = ActivityService(clock=lambda: 0)
    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        result = await service.get("owner/repo", client)
        assert result["commits"]["status"] != "available"
        assert result["deployments"]["status"] == "available"
        assert await service.get("owner/repo", client) == result
        assert calls == 2


async def test_stale_data_retained_and_pagination_bounded():
    now = [0]
    failing = [False]
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if failing[0]:
            return httpx.Response(503)
        return (
            httpx.Response(
                200,
                json=[commit()],
                headers={
                    "Link": '<https://api.github.com/next>; rel="next"',
                },
            )
            if request.url.path.endswith("commits")
            else httpx.Response(200, json=[])
        )

    service = ActivityService(clock=lambda: now[0])
    async with httpx.AsyncClient(
        base_url="https://api.github.com", transport=httpx.MockTransport(handler)
    ) as client:
        first = await service.get("owner/repo", client)
        assert first["commits"]["truncated"]
        assert calls == 4
        now[0] = 61
        failing[0] = True
        second = await service.get("owner/repo", client)
        assert second["commits"]["stale"]
        assert second["commits"]["items"] == first["commits"]["items"]
