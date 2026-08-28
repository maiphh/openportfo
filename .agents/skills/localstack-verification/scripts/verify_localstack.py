#!/usr/bin/env python3
"""Read-only LocalStack contract probe for OpenPortfo DynamoDB and S3."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

import boto3


EXPECTED_KEYS = {
    "users": [("userId", "HASH")],
    "holdings": [("userId", "HASH"), ("sk", "RANGE")],
    "watchlist": [("userId", "HASH"), ("sk", "RANGE")],
    "price-cache": [("pk", "HASH")],
    "news": [("pk", "HASH"), ("sk", "RANGE")],
    "settings": [("pk", "HASH"), ("sk", "RANGE")],
    "fx": [("pk", "HASH"), ("sk", "RANGE")],
    "rss": [("pk", "HASH"), ("sk", "RANGE")],
    "job-runs": [("pk", "HASH"), ("sk", "RANGE")],
    "snapshots": [("userId", "HASH"), ("sk", "RANGE")],
    "chat-idempotency": [("userId", "HASH"), ("requestId", "RANGE")],
}

EXPECTED_TTLS = {"price-cache": "ttl", "chat-idempotency": "expiresAt"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="http://localhost:4566")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--prefix", default="openportfo")
    parser.add_argument("--bucket", default="openportfo-data-local")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    endpoint = args.endpoint.rstrip("/")
    report: dict[str, object] = {"endpoint": endpoint}

    try:
        with urllib.request.urlopen(f"{endpoint}/_localstack/health", timeout=5) as response:
            health = json.load(response)
        services = health.get("services", {})
        for service in ("dynamodb", "s3"):
            if services.get(service) not in {"running", "available"}:
                raise RuntimeError(f"LocalStack service {service} is not ready: {services.get(service)!r}")

        common = {
            "endpoint_url": endpoint,
            "region_name": args.region,
            "aws_access_key_id": "test",
            "aws_secret_access_key": "test",
        }
        dynamodb = boto3.client("dynamodb", **common)
        s3 = boto3.client("s3", **common)

        actual_tables = set(dynamodb.list_tables()["TableNames"])
        expected_tables = {f"{args.prefix}-{suffix}" for suffix in EXPECTED_KEYS}
        missing = sorted(expected_tables - actual_tables)
        if missing:
            raise RuntimeError(f"Missing DynamoDB tables: {', '.join(missing)}")

        checked_keys: dict[str, list[tuple[str, str]]] = {}
        for suffix, expected_schema in EXPECTED_KEYS.items():
            table = f"{args.prefix}-{suffix}"
            description = dynamodb.describe_table(TableName=table)["Table"]
            actual_schema = [(entry["AttributeName"], entry["KeyType"]) for entry in description["KeySchema"]]
            if actual_schema != expected_schema:
                raise RuntimeError(f"Unexpected key schema for {table}: {actual_schema!r}")
            checked_keys[table] = actual_schema

        checked_ttls: dict[str, str] = {}
        for suffix, attribute in EXPECTED_TTLS.items():
            table = f"{args.prefix}-{suffix}"
            ttl = dynamodb.describe_time_to_live(TableName=table)["TimeToLiveDescription"]
            if ttl.get("TimeToLiveStatus") != "ENABLED" or ttl.get("AttributeName") != attribute:
                raise RuntimeError(f"Unexpected TTL contract for {table}: {ttl!r}")
            checked_ttls[table] = attribute

        s3.head_bucket(Bucket=args.bucket)
        report.update(
            {
                "status": "pass",
                "services": {name: services[name] for name in ("dynamodb", "s3")},
                "tables": sorted(expected_tables),
                "keySchemas": checked_keys,
                "ttls": checked_ttls,
                "bucket": args.bucket,
            }
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        report.update({"status": "fail", "error": str(exc)})
        print(json.dumps(report, indent=2, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
