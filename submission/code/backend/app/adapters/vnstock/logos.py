"""VN stock logo URL helpers.

``vnstock`` Company APIs do not expose logos. Use one public CDN everywhere so
heatmap, detail, search, and lists stay consistent (homepage favicons differ).
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

_LOGO_KEYS = (
    "logo",
    "logo_url",
    "logoUrl",
    "image",
    "image_url",
    "imageUrl",
    "icon",
    "icon_url",
    "iconUrl",
)

# Shared with frontend ``vnStockLogoUrl`` — keep paths identical.
_COMPANIES_MARKETCAP = "https://companiesmarketcap.com/img/company-logos/128/{symbol}.VN.png"


def _first_url(row: Optional[dict[str, Any]], keys: Sequence[str] = _LOGO_KEYS) -> Optional[str]:
    if not row:
        return None
    for key in keys:
        raw = row.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text.startswith("http://") or text.startswith("https://"):
            return text
    return None


def stock_logo_url(
    symbol: str,
    *,
    homepage: Optional[str] = None,
    provider_row: Optional[dict[str, Any]] = None,
    explicit: Optional[str] = None,
) -> Optional[str]:
    """Best-effort public logo URL for a Vietnam-listed ticker.

    ``homepage`` is accepted for call-site compatibility but is not used for the
    URL: favicons differ from the CDN used on list surfaces.
    """
    _ = homepage  # reserved; do not derive favicons (breaks cross-page consistency)
    for candidate in (explicit, _first_url(provider_row)):
        if candidate:
            return candidate

    sym = (symbol or "").strip().upper()
    if not sym or not sym.isalnum():
        return None
    return _COMPANIES_MARKETCAP.format(symbol=sym)


__all__ = ["stock_logo_url"]
