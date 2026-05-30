from __future__ import annotations

from contextlib import contextmanager

from leadbot_worker import worker


@contextmanager
def fake_connection_factory():
    yield object()


def test_run_simulated_job_marks_completed(monkeypatch) -> None:
    completed: list[tuple[str, int, int, int]] = []

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        completed.append((job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr(worker.queries, "mark_job_completed", mark_job_completed)

    worker.run_simulated_job(object(), {"id": "job-1"})
    assert completed == [("job-1", 0, 0, 0)]


def test_process_next_job_returns_false_when_queue_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(worker.queries, "claim_next_queued_job", lambda connection: None)

    def job_runner(connection, job):
        raise AssertionError("job runner should not be called for an empty queue")

    processed = worker.process_next_job(
        fake_connection_factory,
        job_runner,
    )

    assert processed is False


def test_process_next_job_claims_and_runs_job(monkeypatch) -> None:
    job = {"id": "job-1"}
    events: list[str] = []

    def claim_next_queued_job(connection):
        events.append("claim")
        return job

    def job_runner(connection, claimed_job):
        events.append(f"run:{claimed_job['id']}")

    monkeypatch.setattr(worker.queries, "claim_next_queued_job", claim_next_queued_job)

    processed = worker.process_next_job(fake_connection_factory, job_runner)

    assert processed is True
    assert events == ["claim", "run:job-1"]


def test_process_next_job_marks_failed_when_runner_raises(monkeypatch) -> None:
    failed: list[tuple[str, str]] = []

    monkeypatch.setattr(worker.queries, "claim_next_queued_job", lambda connection: {"id": "job-1"})

    def job_runner(connection, job):
        raise RuntimeError("boom")

    def mark_job_failed(connection, job_id, error_message):
        failed.append((job_id, error_message))

    monkeypatch.setattr(worker.queries, "mark_job_failed", mark_job_failed)

    processed = worker.process_next_job(fake_connection_factory, job_runner)

    assert processed is True
    assert failed == [("job-1", "boom")]


def test_process_next_job_marks_failed_when_runner_returns_value(monkeypatch) -> None:
    failed: list[tuple[str, str]] = []

    monkeypatch.setattr(worker.queries, "claim_next_queued_job", lambda connection: {"id": "job-1"})

    def mark_job_failed(connection, job_id, error_message):
        failed.append((job_id, error_message))

    monkeypatch.setattr(worker.queries, "mark_job_failed", mark_job_failed)

    processed = worker.process_next_job(fake_connection_factory, lambda connection, job: False)

    assert processed is True
    assert failed == [("job-1", "Job runners must raise on failure and return None")]
