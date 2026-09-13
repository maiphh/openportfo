"""Infrastructure contract for the production chat idempotency ledger."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_eb_policy_can_manage_chat_idempotency_ledger() -> None:
    policy = json.loads((ROOT / "infra" / "iam" / "eb-instance-policy.json").read_text(encoding="utf-8"))
    statement = next(item for item in policy["Statement"] if item.get("Sid") == "DynamoDBRW")
    actions = set(statement["Action"])
    assert {"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem"} <= actions
    assert any(str(resource).endswith(":table/openportfo-chat-idempotency") for resource in statement["Resource"])


def test_cloudformation_wires_chat_table_to_eb_and_exports_name() -> None:
    template = (ROOT / "infra" / "cloudformation.yml").read_text(encoding="utf-8")
    assert "- !GetAtt ChatIdempotencyTable.Arn" in template
    assert "ChatIdempotencyTableName:" in template
    assert "Value: !Ref ChatIdempotencyTable" in template


def test_chat_table_name_documentation_covers_project_prefix() -> None:
    env_example = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    infra_readme = (ROOT / "infra" / "README.md").read_text(encoding="utf-8")
    assert "CHAT_IDEMPOTENCY_TABLE" in env_example
    assert "<ProjectPrefix>-chat-idempotency" in env_example
    assert "ChatIdempotencyTableName" in infra_readme
    assert "<ProjectPrefix>-chat-idempotency" in infra_readme
