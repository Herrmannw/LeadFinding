from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from psycopg import Connection

from leadbot_worker.db import queries

ConnectionFactory = Callable[[], AbstractContextManager[Connection]]
JobRunner = Callable[[Connection, dict[str, Any]], bool]


def run_simulated_job(connection: Connection, job: dict[str, Any]) -> bool:
    queries.mark_job_completed(
        connection,
        job["id"],
        records_found=0,
        leads_created=0,
        qualified_leads=0,
    )
    return True


def process_next_job(connection_factory: ConnectionFactory, job_runner: JobRunner) -> bool:
    with connection_factory() as connection:
        job = queries.claim_next_queued_job(connection)

    if job is None:
        return False

    with connection_factory() as connection:
        try:
            job_runner(connection, job)
        except Exception as exc:  # noqa: BLE001 - workers should persist job failures.
            queries.mark_job_failed(connection, job["id"], str(exc))

    return True
