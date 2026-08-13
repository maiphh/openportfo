"""HTTP + feedparser RSS fetcher (adapter only; no boto3)."""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from ipaddress import ip_address
from time import mktime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.ports.rss import RssItem

_LOOPBACK_HOSTS = frozenset({"localhost", "localhost.localdomain"})
_MAX_REDIRECTS = 5


def _ip_is_blocked(ip: Any) -> bool:
    if ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_reserved
        or ip.is_multicast
    )


def _host_is_blocked(host: str | None) -> bool:
    hostname = (host or "").strip().lower().rstrip(".")
    if not hostname:
        return True
    if hostname in _LOOPBACK_HOSTS:
        return True
    try:
        ip = ip_address(hostname)
    except ValueError:
        return False
    return _ip_is_blocked(ip)


def _assert_resolved_public(hostname: str) -> None:
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError as exc:
        raise ValueError("URL host is not allowed") from exc
    if not infos:
        raise ValueError("URL host is not allowed")
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            raise ValueError("URL host is not allowed")
        host_ip = sockaddr[0]
        if isinstance(host_ip, bytes):
            host_ip = host_ip.decode()
        host_ip = str(host_ip)
        if "%" in host_ip:
            host_ip = host_ip.split("%", 1)[0]
        try:
            ip = ip_address(host_ip)
        except ValueError as exc:
            raise ValueError("URL host is not allowed") from exc
        if _ip_is_blocked(ip):
            raise ValueError("URL host is not allowed")


def assert_public_http_url(url: str) -> None:
    """Reject non-http(s) URLs and hosts that resolve to non-public addresses."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must be http(s) with a host")
    hostname = parsed.hostname
    if _host_is_blocked(hostname):
        raise ValueError("URL host is not allowed")
    host = (hostname or "").strip().lower().rstrip(".")
    try:
        ip_address(host)
    except ValueError:
        _assert_resolved_public(host)


def _assert_public_http_url(url: str) -> None:
    assert_public_http_url(url)


try:
    import feedparser
except ImportError:  # pragma: no cover — optional until installed
    feedparser = None  # type: ignore[assignment]


def _struct_time_to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(mktime(value), tz=timezone.utc)
    except (TypeError, OverflowError, ValueError, OSError):
        return None


def _parse_published(entry: Any) -> Optional[datetime]:
    if getattr(entry, "published_parsed", None):
        dt = _struct_time_to_dt(entry.published_parsed)
        if dt:
            return dt
    if getattr(entry, "updated_parsed", None):
        dt = _struct_time_to_dt(entry.updated_parsed)
        if dt:
            return dt
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if not raw:
            continue
        try:
            return parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, IndexError):
            try:
                s = str(raw).replace("Z", "+00:00")
                return datetime.fromisoformat(s)
            except ValueError:
                continue
    return None


class HttpRssFetcher:
    """Fetch RSS/Atom via httpx and parse with feedparser."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        transport: Optional[httpx.BaseTransport] = None,
        user_agent: str = "OpenPortfoRSS/1.0",
    ) -> None:
        self._timeout = timeout_seconds
        self._transport = transport
        self._user_agent = user_agent

    def fetch(self, url: str) -> list[RssItem]:
        if feedparser is None:
            raise RuntimeError(
                "feedparser is not installed; add feedparser to requirements for RSS jobs"
            )
        try:
            _assert_public_http_url(url)
            content = self._get_public_feed(url)
        except httpx.HTTPError:
            return []
        except ValueError:
            return []

        parsed = feedparser.parse(content)
        source_name = getattr(parsed.feed, "title", None) if getattr(parsed, "feed", None) else None
        items: list[RssItem] = []
        for entry in getattr(parsed, "entries", []) or []:
            title = (getattr(entry, "title", None) or "").strip()
            link = (getattr(entry, "link", None) or "").strip()
            if not title and not link:
                continue
            items.append(
                RssItem(
                    title=title or link,
                    url=link or title,
                    published_at=_parse_published(entry),
                    source_name=source_name,
                )
            )
        return items

    def _get_public_feed(self, url: str) -> str:
        current = url
        with httpx.Client(
            timeout=self._timeout,
            transport=self._transport,
            follow_redirects=False,
            headers={"User-Agent": self._user_agent},
        ) as client:
            for _ in range(_MAX_REDIRECTS + 1):
                _assert_public_http_url(current)
                resp = client.get(current)
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise httpx.HTTPError("Redirect missing Location")
                    current = str(resp.url.join(location))
                    continue
                resp.raise_for_status()
                return resp.text
        raise httpx.HTTPError("Too many redirects")


__all__ = ["HttpRssFetcher", "assert_public_http_url"]
