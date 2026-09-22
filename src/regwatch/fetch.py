"""HTTP fetching with polite defaults. Failures are data, not crashes."""
from __future__ import annotations

import urllib.error
import urllib.request

USER_AGENT = "regwatch/0.1 (+https://github.com/ram-polisetti/regulatory-change-watcher; research demo)"


class FetchError(Exception):
    """A fetch failed; carries what we know so it can be audit-logged."""


def fetch(url: str, timeout: int = 30) -> tuple[int, str, bytes]:
    """Return (status, final_url, body). Raises FetchError on any failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.url, resp.read()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"URL error for {url}: {e.reason}") from e
    except Exception as e:  # timeouts etc.
        raise FetchError(f"fetch failed for {url}: {e}") from e
