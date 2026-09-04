"""Bounded standard-library clients for authoritative citation sources."""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from typing import Any


INSPIRE_API = "https://inspirehep.net/api/literature"
ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
ALLOWED_ONLINE_HOSTS = {
    "api.crossref.org",
    "export.arxiv.org",
    "inspirehep.net",
    "www.inspirehep.net",
}
USER_AGENT = "scientific-research-workbench/0.5"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


def normalize_arxiv(value: str) -> str:
    value = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", value.strip(), flags=re.I)
    value = re.sub(r"^arxiv:\s*", "", value, flags=re.I)
    value = re.sub(r"\.pdf$", "", value, flags=re.I)
    return re.sub(r"v\d+$", "", value, flags=re.I).lower()


def normalize_doi(value: str) -> str:
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I)
    return re.sub(r"^doi:\s*", "", value, flags=re.I).lower()


def request_bytes(
    url: str, timeout: float, retries: int, accept: str
) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": accept},
    )
    context = ssl.create_default_context()
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or final.hostname not in ALLOWED_ONLINE_HOSTS:
                    raise OSError(f"unexpected redirect target: {response.geturl()}")
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise OSError("online response exceeds size limit")
                return payload
        except (OSError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(1.0 * (attempt + 1), 3.0))
    assert last_error is not None
    raise OSError(str(last_error))


def request_json(url: str, timeout: float, retries: int) -> dict[str, Any]:
    try:
        return json.loads(
            request_bytes(url, timeout, retries, "application/json").decode(
                "utf-8", errors="strict"
            )
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OSError(f"invalid JSON response: {exc}") from exc
