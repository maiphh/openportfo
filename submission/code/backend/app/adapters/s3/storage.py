"""S3 ObjectStorage adapter (boto3 confined here)."""

from __future__ import annotations

import json
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError


class S3ObjectStorage:
    """JSON blob store on S3 for history/ and snapshots/ keys."""

    def __init__(
        self,
        bucket: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        client=None,
    ) -> None:
        if not bucket:
            raise ValueError("S3ObjectStorage requires a non-empty bucket name")
        self.bucket = bucket
        if client is not None:
            self._client = client
        else:
            kwargs: dict[str, Any] = {"region_name": region or "us-east-1"}
            if endpoint_url:
                kwargs["endpoint_url"] = endpoint_url
                kwargs["aws_access_key_id"] = "test"
                kwargs["aws_secret_access_key"] = "test"
            self._client = boto3.client("s3", **kwargs)

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            code = (exc.response or {}).get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return None
            raise
        body = resp["Body"].read()
        if not body:
            return None
        data = json.loads(body.decode("utf-8"))
        return data if isinstance(data, dict) else None

    def put_json(self, key: str, data: dict[str, Any]) -> None:
        payload = json.dumps(data, default=str).encode("utf-8")
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            ContentType="application/json",
        )

    def ping(self) -> None:
        self._client.head_bucket(Bucket=self.bucket)

    def list_keys(self, prefix: str = "", *, limit: int = 100) -> list[str]:
        cap = max(1, min(int(limit), 500))
        resp = self._client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix or "",
            MaxKeys=cap,
        )
        return [str(obj["Key"]) for obj in (resp.get("Contents") or []) if obj.get("Key")]


__all__ = ["S3ObjectStorage"]
