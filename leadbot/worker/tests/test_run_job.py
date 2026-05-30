from leadbot_worker.pipeline.collect_urls import MockSerpProvider
from leadbot_worker.pipeline.run_job import run_parse_pages_job, run_url_collection_job
from leadbot_worker.models.raw_record import ParsedSourceRecord


def test_run_url_collection_job_logs_and_stores_discovered_urls(monkeypatch) -> None:
    events: list[tuple] = []

    def log_api_request(connection, **kwargs):
        events.append(("log", kwargs["query"], kwargs["success"], kwargs["metadata"]["source_name"]))

    def insert_raw_record(connection, search_job_id, record):
        events.append(
            (
                "insert",
                search_job_id,
                record.source_name,
                record.source_url,
                record.parse_status,
            )
        )
        return f"raw-{len(events)}"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", job_id, kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.log_api_request", log_api_request)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_url_collection_job(
        object(),
        {
            "id": "job-1",
            "industry": "HVAC",
            "location": "Houston TX",
            "selected_sources": ["yelp", "thumbtack"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    logged_sources = {event[3] for event in events if event[0] == "log"}
    inserted_urls = [event[3] for event in events if event[0] == "insert"]

    assert logged_sources == {"yelp", "thumbtack"}
    assert len(inserted_urls) == len(set(inserted_urls)) == 4
    assert all(event[4] == "needs_review" for event in events if event[0] == "insert")
    assert events[-1] == ("completed", "job-1", 4, 0, 0)


def test_run_parse_pages_job_fetches_and_stores_parsed_records(monkeypatch) -> None:
    events: list[tuple] = []

    def log_api_request(connection, **kwargs):
        events.append(("log", kwargs["metadata"]["source_name"]))

    def fetch_and_parse(source_url):
        return ParsedSourceRecord(
            source_name=source_url.source_name,
            source_url=str(source_url.url),
            query_used=source_url.query_used,
            business_name=f"Parsed {source_url.source_name}",
            parse_status="parsed",
            parse_confidence=0.9,
        )

    def insert_raw_record(connection, search_job_id, record):
        events.append(("insert", search_job_id, record.source_name, record.parse_status))
        return f"raw-{len(events)}"

    def update_job_progress(connection, job_id, **kwargs):
        events.append(("progress", job_id, kwargs))

    def mark_job_completed(connection, job_id, records_found, leads_created, qualified_leads):
        events.append(("completed", job_id, records_found, leads_created, qualified_leads))

    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.log_api_request", log_api_request)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.fetch_and_parse", fetch_and_parse)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.insert_raw_record", insert_raw_record)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.update_job_progress", update_job_progress)
    monkeypatch.setattr("leadbot_worker.pipeline.run_job.queries.mark_job_completed", mark_job_completed)

    run_parse_pages_job(
        object(),
        {
            "id": "job-1",
            "industry": "HVAC",
            "location": "Houston TX",
            "selected_sources": ["yelp"],
            "target_record_count": 10,
        },
        MockSerpProvider(),
    )

    assert [event for event in events if event[0] == "insert"] == [
        ("insert", "job-1", "yelp", "parsed"),
        ("insert", "job-1", "yelp", "parsed"),
    ]
    assert events[-1] == ("completed", "job-1", 2, 0, 0)
