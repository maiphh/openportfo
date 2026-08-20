"""DynamoDB UserProfileRepo.

Table: openportfo-users
PK: userId
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Optional, Sequence

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    utc_now,
)
from app.ports.users import Role, UserProfile
from app.services.currency_service import normalize_stored_currency


def profile_to_item(profile: UserProfile) -> dict[str, Any]:
    """Map domain profile → Dynamo item (pure; unit-testable)."""
    return sanitize_for_dynamo(
        {
            "userId": profile.user_id,
            "email": profile.email,
            "name": profile.name,
            "role": profile.role,
            "newsKeywords": list(profile.news_keywords or []),
            "emailOptIn": bool(profile.email_opt_in),
            "preferredCurrency": normalize_stored_currency(profile.preferred_currency),
            "createdAt": dt_to_iso(profile.created_at),
            "updatedAt": dt_to_iso(profile.updated_at),
        }
    )


def item_to_profile(item: dict[str, Any]) -> UserProfile:
    """Map Dynamo item → domain profile (pure; unit-testable)."""
    return UserProfile(
        user_id=str(item["userId"]),
        email=item.get("email"),
        name=item.get("name"),
        role=item.get("role") or "user",  # type: ignore[arg-type]
        news_keywords=list(item.get("newsKeywords") or []),
        email_opt_in=bool(item.get("emailOptIn", False)),
        preferred_currency=normalize_stored_currency(item.get("preferredCurrency")),
        created_at=iso_to_dt(item.get("createdAt")) or utc_now(),
        updated_at=iso_to_dt(item.get("updatedAt")) or utc_now(),
    )


class DynamoUserProfileRepo:
    """User profiles keyed by Cognito sub (userId)."""

    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def get(self, user_id: str) -> Optional[UserProfile]:
        resp = self._table.get_item(Key={"userId": user_id})
        item = resp.get("Item")
        return item_to_profile(item) if item else None

    def get_or_create(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        existing = self.get(user_id)
        if existing is not None:
            changed = False
            if email and not existing.email:
                existing.email = email
                changed = True
            if name and not existing.name:
                existing.name = name
                changed = True
            if changed:
                existing.updated_at = utc_now()
                self._table.put_item(Item=profile_to_item(existing))
            return existing

        now = utc_now()
        profile = UserProfile(
            user_id=user_id,
            email=email,
            name=name,
            role="user",
            news_keywords=[],
            email_opt_in=False,
            created_at=now,
            updated_at=now,
        )
        self._table.put_item(Item=profile_to_item(profile))
        return profile

    def update_settings(
        self,
        user_id: str,
        *,
        news_keywords: Optional[Sequence[str]] = None,
        email_opt_in: Optional[bool] = None,
        preferred_currency: Optional[str] = None,
    ) -> UserProfile:
        profile = self.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        if news_keywords is not None:
            profile.news_keywords = list(news_keywords)
        if email_opt_in is not None:
            profile.email_opt_in = email_opt_in
        if preferred_currency is not None:
            profile.preferred_currency = normalize_stored_currency(preferred_currency)
        profile.updated_at = utc_now()
        self._table.put_item(Item=profile_to_item(profile))
        return profile

    def set_role(self, user_id: str, role: Role) -> UserProfile:
        profile = self.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        profile.role = role
        profile.updated_at = utc_now()
        self._table.put_item(Item=profile_to_item(profile))
        return profile

    def iter_pages(
        self,
        *,
        page_size: Optional[int] = None,
    ) -> Iterator[list[UserProfile]]:
        """Yield one DynamoDB scan page at a time.

        DynamoDB's ``LastEvaluatedKey`` is an opaque cursor and must be sent
        back as ``ExclusiveStartKey`` on the next scan.  Keeping the cursor
        local to this generator makes pagination correct without retaining
        prior pages in the job process.
        """
        kwargs: dict[str, Any] = {}
        if page_size is not None:
            kwargs["Limit"] = max(1, int(page_size))

        while True:
            response = self._table.scan(**kwargs)
            page = [item_to_profile(item) for item in response.get("Items") or []]
            if page:
                yield page
            cursor = response.get("LastEvaluatedKey")
            if not cursor:
                return
            kwargs = {"ExclusiveStartKey": cursor}
            if page_size is not None:
                kwargs["Limit"] = max(1, int(page_size))

    def iter_all(self, *, page_size: Optional[int] = None) -> Iterator[UserProfile]:
        """Lazily scan all profiles, releasing each page after consumption."""
        for page in self.iter_pages(page_size=page_size):
            yield from page

    def list_all(self) -> list[UserProfile]:
        """Compatibility materializing helper for non-job callers."""
        return list(self.iter_all())


__all__ = ["DynamoUserProfileRepo", "profile_to_item", "item_to_profile"]
