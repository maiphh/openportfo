"""DynamoDB JobRunsRepo.

Table: openportfo-job-runs
PK: JOB#{type}  SK: {runAt ISO}#{runId}
"""

from __future__ import annotations

from typing import Any, Optional

from boto3.dynamodb.conditions import Key

from app.adapters.dynamodb.base import (
    deep_from_dynamo,
    dt_to_iso,
    get_table,
    iso_to_dt,
    sanitize_for_dynamo,
    utc_now,
)
from app.ports.admin import JobRun


def job_pk(job_type: str) -> str:
    return f"JOB#{job_type}"


def job_sk(run: JobRun) -> str:
    started = dt_to_iso(run.started_at) or dt_to_iso(utc_now()) or ""
    return f"{started}#{run.run_id}"


def job_to_item(run: JobRun) -> dict[str, Any]:
    return sanitize_for_dynamo(
        {
            "pk": job_pk(run.job_type),
            "sk": job_sk(run),
            "runId": run.run_id,
            "jobType": run.job_type,
            "status": run.status,
            "startedAt": dt_to_iso(run.started_at),
            "finishedAt": dt_to_iso(run.finished_at),
            "message": run.message,
            "counts": run.counts or {},
        }
    )


def item_to_job(item: dict[str, Any]) -> JobRun:
    counts = item.get("counts") or {}
    if isinstance(counts, dict):
        counts = deep_from_dynamo(counts)
    return JobRun(
        run_id=str(item.get("runId") or ""),
        job_type=str(item.get("jobType") or ""),
        status=str(item.get("status") or ""),
        started_at=iso_to_dt(item.get("startedAt")),
        finished_at=iso_to_dt(item.get("finishedAt")),
        message=item.get("message"),
        counts=counts if isinstance(counts, dict) else {},
    )


class DynamoJobRunsRepo:
    def __init__(
        self,
        table_name: str,
        *,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        table=None,
    ) -> None:
        self._table = table or get_table(table_name, region=region, endpoint_url=endpoint_url)

    def put(self, run: JobRun) -> None:
        self._table.put_item(Item=job_to_item(run))

    def list_recent(self, job_type: Optional[str] = None, limit: int = 50) -> list[JobRun]:
        runs: list[JobRun] = []
        if job_type:
            resp = self._table.query(
                KeyConditionExpression=Key("pk").eq(job_pk(job_type)),
                ScanIndexForward=False,
                Limit=max(1, limit),
            )
            runs = [item_to_job(i) for i in resp.get("Items") or []]
        else:
            # Scan all job types (demo scale)
            resp = self._table.scan()
            for raw in resp.get("Items") or []:
                runs.append(item_to_job(raw))
            while resp.get("LastEvaluatedKey"):
                resp = self._table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
                for raw in resp.get("Items") or []:
                    runs.append(item_to_job(raw))

            def _key(r: JobRun) -> str:
                return r.started_at.isoformat() if r.started_at else ""

            runs.sort(key=_key, reverse=True)
            runs = runs[: max(0, limit)]
        return runs


__all__ = [
    "DynamoJobRunsRepo",
    "job_pk",
    "job_sk",
    "job_to_item",
    "item_to_job",
]
