"""BL-028: HttpRssFetcher raises typed RssFetchError; SSRF + UTC dates."""

from __future__ import annotations

from datetime import timezone

import httpx
import pytest

from app.adapters.rss.fetcher import HttpRssFetcher, assert_public_http_url
from app.ports.rss import RssFetchError, RssItem

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Bitcoin rises</title>
      <link>https://example.com/btc</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>ETH update</title>
    <link href="https://example.com/eth"/>
    <updated>2024-06-15T08:30:00Z</updated>
  </entry>
</feed>
"""


def test_fetch_parses_rss_atom_and_utc_published_at() -> None:
    bodies = {
        "https://example.com/rss.xml": RSS_XML,
        "https://example.com/atom.xml": ATOM_XML,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=bodies[str(request.url)])

    fetcher = HttpRssFetcher(transport=httpx.MockTransport(handler))
    rss_items = fetcher.fetch("https://example.com/rss.xml")
    assert len(rss_items) == 1
    assert isinstance(rss_items[0], RssItem)
    assert rss_items[0].title == "Bitcoin rises"
    assert rss_items[0].url == "https://example.com/btc"
    assert rss_items[0].published_at is not None
    assert rss_items[0].published_at.tzinfo is not None
    assert rss_items[0].published_at.astimezone(timezone.utc).year == 2024

    atom_items = fetcher.fetch("https://example.com/atom.xml")
    assert len(atom_items) == 1
    assert atom_items[0].title == "ETH update"
    assert atom_items[0].published_at is not None
    assert atom_items[0].published_at.tzinfo is not None


def test_fetch_raises_rss_fetch_error_on_http_transport_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    fetcher = HttpRssFetcher(transport=httpx.MockTransport(handler))
    with pytest.raises(RssFetchError):
        fetcher.fetch("https://example.com/feed.xml")


def test_fetch_raises_on_non_2xx() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    fetcher = HttpRssFetcher(transport=httpx.MockTransport(handler))
    with pytest.raises(RssFetchError):
        fetcher.fetch("https://example.com/feed.xml")


def test_fetch_rejects_private_loopback_and_link_local_hosts() -> None:
    fetcher = HttpRssFetcher(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=RSS_XML))
    )
    for bad in (
        "https://127.0.0.1/feed.xml",
        "http://localhost/feed.xml",
        "https://10.0.0.5/rss",
        "https://192.168.1.1/rss",
        "https://169.254.1.1/meta",
        "ftp://example.com/feed",
        "not-a-url",
    ):
        with pytest.raises(RssFetchError):
            fetcher.fetch(bad)
        with pytest.raises(ValueError):
            assert_public_http_url(bad)


def test_fetch_rejects_unsafe_redirect_target_and_redirect_exhaustion() -> None:
    def unsafe_redirect(request: httpx.Request) -> httpx.Response:
        if "start" in str(request.url):
            return httpx.Response(
                302, headers={"location": "http://127.0.0.1/secret"}
            )
        return httpx.Response(200, text=RSS_XML)

    fetcher = HttpRssFetcher(transport=httpx.MockTransport(unsafe_redirect))
    with pytest.raises(RssFetchError):
        fetcher.fetch("https://example.com/start")

    hops = {"n": 0}

    def endless(request: httpx.Request) -> httpx.Response:
        hops["n"] += 1
        return httpx.Response(
            302, headers={"location": f"https://example.com/hop{hops['n']}"}
        )

    fetcher2 = HttpRssFetcher(transport=httpx.MockTransport(endless))
    with pytest.raises(RssFetchError):
        fetcher2.fetch("https://example.com/hop0")

    def missing_location(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    fetcher3 = HttpRssFetcher(transport=httpx.MockTransport(missing_location))
    with pytest.raises(RssFetchError):
        fetcher3.fetch("https://example.com/redir")
