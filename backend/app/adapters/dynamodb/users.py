"""DynamoDB UserProfileRepo.

Table: openportfo-users
PK: userId
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Optional, Sequence

from botocore.exceptions import ClientError

from app.adapters.dynamodb.base import (
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    TypeSerializer,
    utc_now,
)
from app.ports.users import UNSET, Role, UserProfile, UserSettingsPatch
from app.services.currency_service import normalize_stored_currency
from app.services.admin_user_service import LastAdminError, RoleConflictError


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
            "avatarStyle": profile.avatar_style,
            "avatarSeed": profile.avatar_seed,
            "avatarColor": profile.avatar_color,
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
        avatar_style=item.get("avatarStyle"),
        avatar_seed=item.get("avatarSeed"),
        avatar_color=item.get("avatarColor"),
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
        role_guard_table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)
        self._role_guard_table = role_guard_table

    def get(self, user_id: str) -> Optional[UserProfile]:
        resp = self._table.get_item(Key={"userId": user_id}, ConsistentRead=True)
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
            # Verified identity refresh is performed through update_identity
            # by the auth dependency. Avoid a whole-item PutItem here: a
            # stale read must never overwrite a concurrent role/settings
            # update.
            return existing

        now = utc_now()
        profile = UserProfile(
            user_id=user_id,
            email=email,
            name=name,
            role="user",
            news_keywords=[],
            email_opt_in=False,
            preferred_currency=None,
            avatar_style=None,
            avatar_seed=None,
            avatar_color=None,
            created_at=now,
            updated_at=now,
        )
        try:
            self._table.put_item(
                Item=profile_to_item(profile),
                ConditionExpression="attribute_not_exists(#userId)",
                ExpressionAttributeNames={"#userId": "userId"},
            )
            return profile
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
            # Another first-auth request won the conditional create.  The
            # follow-up is strongly consistent and must be returned as-is so
            # role/settings changes are never overwritten by stale claims.
            winner = self.get(user_id)
            if winner is None:
                raise KeyError(f"User not found after concurrent create: {user_id}") from exc
            return winner

    def update_settings(
        self,
        user_id: str,
        patch: Optional[UserSettingsPatch] = None,
        *,
        news_keywords: object = UNSET,
        email_opt_in: object = UNSET,
        preferred_currency: object = UNSET,
        avatar_style: object = UNSET,
        avatar_seed: object = UNSET,
        avatar_color: object = UNSET,
    ) -> UserProfile:
        patch = patch or UserSettingsPatch(
            news_keywords=news_keywords,
            email_opt_in=email_opt_in,
            preferred_currency=preferred_currency,
            avatar_style=avatar_style,
            avatar_seed=avatar_seed,
            avatar_color=avatar_color,
        )
        set_parts: list[str] = []
        remove_parts: list[str] = []
        names: dict[str, str] = {}
        values: dict[str, Any] = {":updatedAt": dt_to_iso(utc_now())}

        def add(field: str, attribute: str, value: object, *, normalize=None) -> None:
            name = f"#{field}"
            names[name] = attribute
            if value is None:
                remove_parts.append(name)
            else:
                set_parts.append(f"{name} = :{field}")
                values[f":{field}"] = normalize(value) if normalize else value

        if patch.news_keywords is not UNSET:
            add("newsKeywords", "newsKeywords", list(patch.news_keywords or []))
        if patch.email_opt_in is not UNSET:
            add("emailOptIn", "emailOptIn", bool(patch.email_opt_in))
        if patch.preferred_currency is not UNSET:
            add("preferredCurrency", "preferredCurrency", patch.preferred_currency, normalize=normalize_stored_currency)
        if patch.avatar_style is not UNSET:
            add("avatarStyle", "avatarStyle", patch.avatar_style)
        if patch.avatar_seed is not UNSET:
            add("avatarSeed", "avatarSeed", patch.avatar_seed)
        if patch.avatar_color is not UNSET:
            add("avatarColor", "avatarColor", patch.avatar_color)

        set_parts.append("#updatedAt = :updatedAt")
        names["#updatedAt"] = "updatedAt"
        expression = "SET " + ", ".join(set_parts)
        if remove_parts:
            expression += " REMOVE " + ", ".join(remove_parts)
        names["#userId"] = "userId"
        try:
            response = self._table.update_item(
                Key={"userId": user_id},
                UpdateExpression=expression,
                ConditionExpression="attribute_exists(#userId)",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=sanitize_for_dynamo(values),
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if _is_conditional_failure(exc):
                raise KeyError(f"User not found: {user_id}") from exc
            raise
        item = response.get("Attributes") or {}
        if not item:
            profile = self.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            return profile
        return item_to_profile(item)

    def update_identity(
        self,
        user_id: str,
        *,
        email: Optional[str] = None,
        name: Optional[str] = None,
    ) -> UserProfile:
        """Refresh verified claims with a field-only update."""
        set_parts: list[str] = []
        names: dict[str, str] = {}
        values: dict[str, Any] = {":updatedAt": dt_to_iso(utc_now())}
        if email:
            names["#email"] = "email"
            values[":email"] = email
            set_parts.append("#email = :email")
        if name:
            names["#name"] = "name"
            values[":name"] = name
            set_parts.append("#name = :name")
        names["#updatedAt"] = "updatedAt"
        set_parts.append("#updatedAt = :updatedAt")
        names["#userId"] = "userId"
        try:
            response = self._table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET " + ", ".join(set_parts),
                ConditionExpression="attribute_exists(#userId)",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=sanitize_for_dynamo(values),
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if _is_conditional_failure(exc):
                raise KeyError(f"User not found: {user_id}") from exc
            raise
        item = response.get("Attributes") or {}
        if not item:
            profile = self.get(user_id)
            if profile is None:
                raise KeyError(f"User not found: {user_id}")
            return profile
        return item_to_profile(item)

    def set_role(self, user_id: str, role: Role) -> UserProfile:
        now = dt_to_iso(utc_now())
        names = {"#role": "role", "#updatedAt": "updatedAt", "#userId": "userId"}
        try:
            response = self._table.update_item(
                Key={"userId": user_id},
                UpdateExpression="SET #role = :role, #updatedAt = :updatedAt",
                ConditionExpression="attribute_exists(#userId)",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues={":role": role, ":updatedAt": now},
                ReturnValues="ALL_NEW",
            )
        except ClientError as exc:
            if _is_conditional_failure(exc):
                raise KeyError(f"User not found: {user_id}") from exc
            raise
        item = response.get("Attributes") or {}
        if item:
            return item_to_profile(item)
        profile = self.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        return profile

    def change_role_guarded(self, user_id: str, role: Role) -> UserProfile:
        """Dynamo transaction for a last-admin-safe demotion.

        The optional guard table is supplied by the dependency factory.  A
        plain ``set_role`` remains useful for idempotent grants and test
        fixtures, while demotions in AWS use the transaction path.
        """
        if role == "admin" or self._role_guard_table is None:
            return self.set_role(user_id, role)

        target = self.get(user_id)
        if target is None:
            raise KeyError(f"User not found: {user_id}")
        if target.role != "admin":
            raise RoleConflictError("Role changed concurrently")

        def admin_count() -> int:
            count = 0
            kwargs: dict[str, Any] = {
                "ConsistentRead": True,
                "ProjectionExpression": "#userId, #role",
                "ExpressionAttributeNames": {"#userId": "userId", "#role": "role"},
            }
            while True:
                response = self._table.scan(**kwargs)
                count += sum(1 for item in response.get("Items") or [] if item.get("role") == "admin")
                continuation = response.get("LastEvaluatedKey")
                if not continuation:
                    return count
                kwargs["ExclusiveStartKey"] = continuation

        users_name = getattr(self._table, "name", "users") or "users"
        guard_name = getattr(self._role_guard_table, "name", "settings") or "settings"
        client = self._table.meta.client
        for attempt in range(2):
            if admin_count() <= 1:
                raise LastAdminError("At least one admin is required")
            guard = self._role_guard_table.get_item(
                Key={"pk": "ADMIN_ROLE_GUARD", "sk": "GLOBAL"},
                ConsistentRead=True,
            ).get("Item") or {}
            version = int(guard.get("version", 0))
            now = dt_to_iso(utc_now())
            try:
                client.transact_write_items(
                    TransactItems=[
                        {
                            "Update": {
                                "TableName": users_name,
                                "Key": _serialize_client_key({"userId": user_id}),
                                "UpdateExpression": "SET #role = :user, #updatedAt = :updatedAt",
                                "ConditionExpression": "attribute_exists(#userId) AND #role = :admin",
                                "ExpressionAttributeNames": {
                                    "#userId": "userId",
                                    "#role": "role",
                                    "#updatedAt": "updatedAt",
                                },
                                "ExpressionAttributeValues": _serialize_client_values(
                                    {
                                        ":user": "user",
                                        ":admin": "admin",
                                        ":updatedAt": now,
                                    }
                                ),
                            }
                        },
                        {
                            "Update": {
                                "TableName": guard_name,
                                "Key": _serialize_client_key(
                                    {"pk": "ADMIN_ROLE_GUARD", "sk": "GLOBAL"}
                                ),
                                "UpdateExpression": "SET #version = :next, #updatedAt = :updatedAt",
                                "ConditionExpression": "attribute_not_exists(#version) OR #version = :version",
                                "ExpressionAttributeNames": {
                                    "#version": "version",
                                    "#updatedAt": "updatedAt",
                                },
                                "ExpressionAttributeValues": _serialize_client_values(
                                    {
                                        ":next": version + 1,
                                        ":version": version,
                                        ":updatedAt": now,
                                    }
                                ),
                            }
                        },
                    ]
                )
                break
            except ClientError as exc:
                if not _is_conditional_transaction_cancel(exc):
                    raise
                latest = self.get(user_id)
                if latest is None:
                    raise KeyError(f"User not found: {user_id}") from exc
                if latest.role != "admin":
                    raise RoleConflictError("Role changed concurrently") from exc
                if attempt == 1:
                    raise RoleConflictError("Role changed concurrently") from exc
        profile = self.get(user_id)
        if profile is None:
            raise KeyError(f"User not found: {user_id}")
        return profile

    def list_page(
        self,
        *,
        limit: int,
        start_after: Optional[str] = None,
    ) -> tuple[list[UserProfile], Optional[str]]:
        """Scan one bounded page using the opaque user id continuation."""
        kwargs: dict[str, Any] = {
            "Limit": max(1, int(limit)),
            "ConsistentRead": True,
        }
        if start_after:
            kwargs["ExclusiveStartKey"] = {"userId": start_after}
        response = self._table.scan(**kwargs)
        items = [item_to_profile(item) for item in response.get("Items") or []]
        last_key = response.get("LastEvaluatedKey") or {}
        last_id = last_key.get("userId") if isinstance(last_key, dict) else None
        if not last_id and items:
            # A Dynamo scan can return a full page without a continuation.  The
            # API only advertises a cursor when there is another page.
            last_id = None
        return items, str(last_id) if last_id else None

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


_DYNAMO_SERIALIZER = TypeSerializer()


def _serialize_client_values(values: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Convert resource/document values to low-level Dynamo AttributeValues."""
    return {key: _DYNAMO_SERIALIZER.serialize(value) for key, value in values.items()}


def _serialize_client_key(key: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _serialize_client_values(key)


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


def _is_conditional_transaction_cancel(exc: ClientError) -> bool:
    """Return true only for condition-driven transaction cancellation."""
    if exc.response.get("Error", {}).get("Code") != "TransactionCanceledException":
        return False
    reasons = exc.response.get("CancellationReasons") or []
    if not reasons:
        # DynamoDB may omit reasons unless ReturnCancellationReasons is enabled.
        return True
    return all(reason.get("Code") in {"ConditionalCheckFailed", "None"} for reason in reasons)
