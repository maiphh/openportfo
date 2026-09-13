from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_standalone_eb_transaction_policy_is_narrow() -> None:
    policy = json.loads((ROOT / "infra" / "iam" / "eb-instance-policy.json").read_text(encoding="utf-8"))
    broad = next(item for item in policy["Statement"] if item["Sid"] == "DynamoDBRW")
    admin = next(item for item in policy["Statement"] if item["Sid"] == "AdminRoleTransactions")
    assert "dynamodb:TransactWriteItems" not in broad["Action"]
    assert admin["Action"] == ["dynamodb:TransactWriteItems"]
    assert set(admin["Resource"]) == {
        "arn:aws:dynamodb:us-east-1:*:table/openportfo-users",
        "arn:aws:dynamodb:us-east-1:*:table/openportfo-settings",
    }


def test_cloudformation_transaction_permission_is_eb_only_and_two_table_scoped() -> None:
    template = (ROOT / "infra" / "cloudformation.yml").read_text(encoding="utf-8")
    eb_block = template.split("EBInstanceRole:", 1)[1].split("EBInstanceProfile:", 1)[0]
    lambda_block = template.split("LambdaExecutionRole:", 1)[1]
    broad = eb_block.split("Sid: DynamoDBRW", 1)[1].split("Sid: AdminRoleTransactions", 1)[0]
    admin = eb_block.split("Sid: AdminRoleTransactions", 1)[1]
    assert "dynamodb:TransactWriteItems" not in broad
    assert "dynamodb:TransactWriteItems" in admin
    assert "!GetAtt UsersTable.Arn" in admin
    assert "!GetAtt SettingsTable.Arn" in admin
    assert "!GetAtt HoldingsTable.Arn" not in admin
    assert "dynamodb:TransactWriteItems" not in lambda_block
