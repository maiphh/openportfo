"""Shared validation and normalization for self/admin profile patches."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from app.ports.users import UNSET, UserSettingsPatch
from app.services.currency_service import CurrencyValidationError, normalize_currency

AVATAR_STYLES: tuple[str, ...] = (
    "notionists",
    "notionists-neutral",
    "adventurer-neutral",
    "big-smile",
    "lorelei",
    "bottts",
    "thumbs",
    "shapes",
)


class UserSettingsValidationError(ValueError):
    """Safe field-level validation failure for public settings APIs."""

    code = "validation_error"

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors = dict(errors)
        super().__init__("Invalid settings patch")

    @property
    def detail(self) -> dict[str, Any]:
        return {"code": self.code, "errors": dict(self.errors)}


def _text(value: object, *, field: str, maximum: int, allow_tabs_newlines: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must be 1-{maximum} characters")
    for char in normalized:
        category = unicodedata.category(char)
        if category.startswith("C") and not (allow_tabs_newlines and char in "\n\r\t"):
            raise ValueError(f"{field} contains unsupported control characters")
    return normalized


def _get(payload: Mapping[str, object], camel: str, snake: str) -> tuple[bool, object]:
    if camel in payload:
        return True, payload[camel]
    if snake in payload:
        return True, payload[snake]
    return False, UNSET


def normalize_user_settings_patch(payload: Mapping[str, object]) -> UserSettingsPatch:
    """Normalize a camelCase/snake_case mapping into an explicit patch."""

    errors: dict[str, str] = {}
    known = {
        "newsKeywords",
        "news_keywords",
        "emailOptIn",
        "email_opt_in",
        "preferredCurrency",
        "preferred_currency",
        "avatarStyle",
        "avatar_style",
        "avatarSeed",
        "avatar_seed",
        "avatarColor",
        "avatar_color",
    }
    for key in payload:
        if key not in known:
            errors[str(key)] = "is not supported"
    values: dict[str, object] = {
        "news_keywords": UNSET,
        "email_opt_in": UNSET,
        "preferred_currency": UNSET,
        "avatar_style": UNSET,
        "avatar_seed": UNSET,
        "avatar_color": UNSET,
    }

    present, raw = _get(payload, "newsKeywords", "news_keywords")
    if present:
        field = "newsKeywords"
        if raw is None or not isinstance(raw, list):
            errors[field] = "must be an array of strings"
        elif len(raw) > 20:
            errors[field] = "must contain at most 20 items"
        else:
            normalized_keywords: list[str] = []
            seen: set[str] = set()
            for item in raw:
                try:
                    text = _text(item, field=field, maximum=50)
                except ValueError as exc:
                    errors[field] = str(exc)
                    break
                key = text.casefold()
                if key not in seen:
                    normalized_keywords.append(text)
                    seen.add(key)
            if field not in errors:
                values["news_keywords"] = normalized_keywords

    present, raw = _get(payload, "emailOptIn", "email_opt_in")
    if present:
        if not isinstance(raw, bool):
            errors["emailOptIn"] = "must be a boolean"
        else:
            values["email_opt_in"] = raw

    present, raw = _get(payload, "preferredCurrency", "preferred_currency")
    if present:
        if raw is None:
            values["preferred_currency"] = None
        else:
            try:
                values["preferred_currency"] = normalize_currency(raw, field="preferredCurrency")
            except CurrencyValidationError:
                errors["preferredCurrency"] = "must be one of VND, USD, EUR or null"

    present, raw = _get(payload, "avatarStyle", "avatar_style")
    if present:
        if raw is None:
            values["avatar_style"] = None
        elif not isinstance(raw, str) or raw.strip().lower() not in AVATAR_STYLES:
            errors["avatarStyle"] = "must be an allowed avatar style or null"
        else:
            values["avatar_style"] = raw.strip().lower()

    present, raw = _get(payload, "avatarSeed", "avatar_seed")
    if present:
        if raw is None:
            values["avatar_seed"] = None
        else:
            try:
                values["avatar_seed"] = _text(raw, field="avatarSeed", maximum=64)
            except ValueError as exc:
                errors["avatarSeed"] = str(exc)

    present, raw = _get(payload, "avatarColor", "avatar_color")
    if present:
        if raw is None:
            values["avatar_color"] = None
        elif not isinstance(raw, str):
            errors["avatarColor"] = "must be RGB, RRGGBB, or null"
        else:
            match = re.fullmatch(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", raw.strip())
            if not match:
                errors["avatarColor"] = "must be RGB, RRGGBB, or null"
            else:
                color = match.group(1).lower()
                values["avatar_color"] = "".join(char * 2 for char in color) if len(color) == 3 else color

    if errors:
        raise UserSettingsValidationError(errors)
    return UserSettingsPatch(**values)


__all__ = [
    "AVATAR_STYLES",
    "UNSET",
    "UserSettingsValidationError",
    "normalize_user_settings_patch",
]
