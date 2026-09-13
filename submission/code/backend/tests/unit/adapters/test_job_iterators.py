"""Pagination and bounded traversal contracts used by scheduled jobs."""

from __future__ import annotations

from decimal import Decimal

from app.adapters.dynamodb.holdings import DynamoHoldingsRepo
from app.adapters.dynamodb.users import DynamoUserProfileRepo
from app.adapters.memory.holdings import InMemoryHoldingsRepo
from app.adapters.memory.users import InMemoryUserProfileRepo
from app.ports.holdings import HoldingRecord


class _PagedScanTable:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def scan(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def test_dynamo_user_pages_follow_last_evaluated_key() -> None:
    table = _PagedScanTable(
        [
            {"Items": [{"userId": "u1"}], "LastEvaluatedKey": {"userId": "u1"}},
            {"Items": [{"userId": "u2"}]},
        ]
    )
    repo = DynamoUserProfileRepo("users", table=table)

    pages = list(repo.iter_pages(page_size=1))

    assert [[profile.user_id for profile in page] for page in pages] == [["u1"], ["u2"]]
    assert table.calls == [
        {"Limit": 1},
        {"ExclusiveStartKey": {"userId": "u1"}, "Limit": 1},
    ]


def test_dynamo_holding_user_pages_dedupe_across_scan_pages() -> None:
    table = _PagedScanTable(
        [
            {
                "Items": [{"userId": "u1"}, {"userId": "u1"}],
                "LastEvaluatedKey": {"userId": "u1", "sk": "HOLD#stock#A"},
            },
            {"Items": [{"userId": "u1"}, {"userId": "u2"}]},
        ]
    )
    repo = DynamoHoldingsRepo("holdings", table=table)

    pages = list(repo.iter_user_pages(page_size=2))

    assert pages == [["u1"], ["u2"]]
    assert table.calls[1]["ExclusiveStartKey"] == {
        "userId": "u1",
        "sk": "HOLD#stock#A",
    }
    assert table.calls[0]["Limit"] == table.calls[1]["Limit"] == 2


def test_memory_adapters_keep_pages_bounded_and_lazy() -> None:
    users = InMemoryUserProfileRepo()
    for index in range(5):
        users.get_or_create(f"u{index}")
    user_pages = list(users.iter_pages(page_size=2))
    assert [len(page) for page in user_pages] == [2, 2, 1]
    assert [profile.user_id for profile in users.iter_all()] == [
        "u0",
        "u1",
        "u2",
        "u3",
        "u4",
    ]

    holdings = InMemoryHoldingsRepo()
    for index in range(5):
        holdings.create(
            HoldingRecord(
                user_id=f"u{index}",
                asset_type="stock",
                symbol="AAA",
                qty=Decimal("1"),
                avg_cost=Decimal("1"),
                currency="VND",
            )
        )
    pages = list(holdings.iter_user_pages(page_size=2))
    assert [len(page) for page in pages] == [2, 2, 1]
    assert list(holdings.iter_all_users()) == ["u0", "u1", "u2", "u3", "u4"]
