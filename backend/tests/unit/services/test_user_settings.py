from __future__ import annotations

import pytest

from app.services.user_settings import (
    AVATAR_STYLES,
    UNSET,
    UserSettingsValidationError,
    normalize_user_settings_patch,
)


def test_normalizes_keywords_and_avatar_fields() -> None:
    patch = normalize_user_settings_patch(
        {
            "newsKeywords": [" BTC ", "btc", "Ｎｅｗｓ"],
            "emailOptIn": True,
            "preferredCurrency": " usd ",
            "avatarStyle": "NOTIONISTS",
            "avatarSeed": "  Ａｄａ  ",
            "avatarColor": "#AbC",
        }
    )
    assert patch.news_keywords == ["BTC", "News"]
    assert patch.email_opt_in is True
    assert patch.preferred_currency == "USD"
    assert patch.avatar_style == "notionists"
    assert patch.avatar_seed == "Ada"
    assert patch.avatar_color == "aabbcc"


def test_omitted_fields_are_unset_and_null_clears_nullable_fields() -> None:
    patch = normalize_user_settings_patch({"preferredCurrency": None, "avatarSeed": None})
    assert patch.news_keywords is UNSET
    assert patch.email_opt_in is UNSET
    assert patch.preferred_currency is None
    assert patch.avatar_seed is None
    assert patch.avatar_style is UNSET
    assert patch.avatar_color is UNSET


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"newsKeywords": None}, "newsKeywords"),
        ({"newsKeywords": ["x"] * 21}, "newsKeywords"),
        ({"newsKeywords": ["\u0000"]}, "newsKeywords"),
        ({"emailOptIn": None}, "emailOptIn"),
        ({"preferredCurrency": "GBP"}, "preferredCurrency"),
        ({"avatarStyle": "unknown"}, "avatarStyle"),
        ({"avatarSeed": "x" * 65}, "avatarSeed"),
        ({"avatarColor": "#12"}, "avatarColor"),
    ],
)
def test_invalid_patch_reports_field_errors_without_values(payload: dict[str, object], field: str) -> None:
    with pytest.raises(UserSettingsValidationError) as exc_info:
        normalize_user_settings_patch(payload)
    assert exc_info.value.errors.get(field)
    assert "GBP" not in str(exc_info.value)
    assert "unknown" not in str(exc_info.value)


def test_allowlist_is_exact() -> None:
    assert AVATAR_STYLES == (
        "notionists",
        "notionists-neutral",
        "adventurer-neutral",
        "big-smile",
        "lorelei",
        "bottts",
        "thumbs",
        "shapes",
    )
