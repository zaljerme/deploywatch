import asyncio
import json
import time
from collections import OrderedDict
from datetime import UTC, datetime

import httpx

from app.config import settings

BASE_URL = "https://api.github.com"
MAX_BYTES = 1024 * 1024


class GitHubUnavailable(Exception):
    def __init__(self, reason, retry_after=60):
        self.reason = reason
        self.retry_after = retry_after


async def fetch_pages(client, repository, kind):
    items = []
    truncated = False
    for page in range(1, 4):
        async with client.stream(
            "GET",
            f"/repos/{repository}/{kind}",
            params={
                "per_page": 20,
                "page": page,
            },
        ) as response:
            if response.headers.get("content-encoding", "identity") != "identity":
                raise GitHubUnavailable("unsupported_encoding")
            if response.status_code in {403, 429}:
                if (
                    response.status_code == 403
                    and response.headers.get("x-ratelimit-remaining") != "0"
                    and "retry-after" not in response.headers
                ):
                    raise GitHubUnavailable("unavailable")
                try:
                    delay = int(response.headers.get("retry-after", "60"))
                    reset = int(response.headers.get("x-ratelimit-reset", "0"))
                    delay = max(delay, reset - int(time.time()))
                except ValueError:
                    delay = 60
                raise GitHubUnavailable("rate_limited", min(3600, max(60, delay)))
            if response.status_code != 200:
                raise GitHubUnavailable("unavailable")
            body = bytearray()
            async for chunk in response.aiter_bytes(8192):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise GitHubUnavailable("response_too_large")
            try:
                data = json.loads(body)
                if not isinstance(data, list):
                    raise ValueError()
                items.extend(normalize(item, kind, repository) for item in data)
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                raise GitHubUnavailable("invalid_response")
            # Never follow a remote Link URL; only advance our own bounded page parameter.
            if "next" not in response.links:
                break
            truncated = page == 3
    return {"status": "available", "items": items[:60], "truncated": truncated}


def normalize(item, kind, repository):
    sha = item["sha"]
    if not isinstance(sha, str) or not sha.isalnum() or len(sha) > 64:
        raise ValueError("invalid SHA")
    if kind == "commits":
        date = item["commit"]["committer"]["date"]
        title = item["commit"]["message"].splitlines()[0][:200]
        url = f"https://github.com/{repository}/commit/{sha}"
    else:
        date = item["created_at"]
        title = f"Deployment record · {str(item['environment'])[:100]}"
        url = f"https://github.com/{repository}/deployments"
    datetime.fromisoformat(date.replace("Z", "+00:00"))
    return {
        "kind": "commit" if kind == "commits" else "deployment",
        "sha": sha,
        "title": title,
        "timestamp": date,
        "url": url,
    }


class ActivityService:
    def __init__(self, clock=time.monotonic):
        self.cache = OrderedDict()
        self.clock = clock
        self.lock = asyncio.Lock()

    async def get(self, repository, client=None):
        async with self.lock:
            entry = self.cache.get(repository)
            if entry and entry[0] > self.clock():
                return entry[1]
            headers = {
                "Accept": "application/vnd.github+json",
                "Accept-Encoding": "identity",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if settings().github_token:
                headers["Authorization"] = f"Bearer {settings().github_token}"
            if client is None:
                async with httpx.AsyncClient(
                    base_url=BASE_URL,
                    headers=headers,
                    timeout=4,
                    follow_redirects=False,
                    trust_env=False,
                ) as owned:
                    return await self._load(repository, owned, entry)
            return await self._load(repository, client, entry)

    async def _load(self, repository, client, entry):
        delays = [60]

        async def load(kind):
            try:
                async with asyncio.timeout(8):
                    return await fetch_pages(client, repository, kind)
            except GitHubUnavailable as exc:
                reason = exc.reason
                delays.append(exc.retry_after)
            except (httpx.HTTPError, TimeoutError):
                reason = "unavailable"
            old = entry[1].get(kind, {}) if entry else {}
            return {
                "status": reason,
                "items": old.get("items", []),
                "stale": bool(old.get("items")),
                "truncated": old.get("truncated", False),
            }

        commits, deployments = await asyncio.gather(load("commits"), load("deployments"))
        result = {
            "repository": repository,
            "commits": commits,
            "deployments": deployments,
            "fetched_at": datetime.now(UTC).isoformat(),
            "notice": "Investigation clues only. Timing does not establish cause. "
            "Deployment records do not confirm successful completion.",
        }
        self.cache[repository] = (self.clock() + max(delays), result)
        self.cache.move_to_end(repository)
        while len(self.cache) > 128:
            self.cache.popitem(last=False)
        return result


activity_service = ActivityService()
