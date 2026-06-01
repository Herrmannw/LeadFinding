from __future__ import annotations

from typing import Any

from psycopg import Connection

from leadbot_worker.db import queries
from leadbot_worker.models.raw_record import ParsedSourceRecord, SourceUrl
from leadbot_worker.pipeline.collect_urls import (
    SerpProvider,
    SerpRequestLog,
    SourceUrlCollection,
    collect_source_url_details,
)
from leadbot_worker.pipeline.dedupe import dedupe_records
from leadbot_worker.pipeline.parse_records import fetch_and_parse
from leadbot_worker.pipeline.score import score_lead


def run_url_collection_job(connection: Connection, job: dict[str, Any], provider: SerpProvider) -> None:
    job_id = job["id"]
    collection = collect_job_source_urls(job, provider)
    log_collection_requests(connection, job_id, collection.request_logs)
    fail_if_all_searches_failed(collection)

    for index, source_url in enumerate(collection.urls, start=1):
        queries.insert_raw_record(
            connection,
            job_id,
            ParsedSourceRecord(
                source_name=source_url.source_name,
                source_url=str(source_url.url),
                query_used=source_url.query_used,
                parse_status="needs_review",
                parse_confidence=0,
                raw_payload={"collection_stage": "url_discovered"},
            ),
        )
        queries.update_job_progress(connection, job_id, records_found=index)

    queries.mark_job_completed(
        connection,
        job_id,
        records_found=len(collection.urls),
        leads_created=0,
        qualified_leads=0,
    )


def run_parse_pages_job(connection: Connection, job: dict[str, Any], provider: SerpProvider) -> None:
    job_id = job["id"]
    collection = collect_job_source_urls(job, provider)
    log_collection_requests(connection, job_id, collection.request_logs)
    fail_if_all_searches_failed(collection)

    raw_records, _raw_record_ids_by_url = fetch_parse_and_store_records(
        connection,
        job_id,
        collection.urls,
    )

    queries.mark_job_completed(
        connection,
        job_id,
        records_found=len(raw_records),
        leads_created=0,
        qualified_leads=0,
    )


def run_search_job(connection: Connection, job: dict[str, Any], provider: SerpProvider) -> None:
    job_id = job["id"]
    collection = collect_job_source_urls(job, provider)
    log_collection_requests(connection, job_id, collection.request_logs)
    fail_if_all_searches_failed(collection)

    raw_records, raw_record_ids_by_url = fetch_parse_and_store_records(
        connection,
        job_id,
        collection.urls,
    )
    parsed_records = [record for record in raw_records if record.parse_status != "failed"]
    leads = dedupe_records(parsed_records)
    qualified_count = 0

    for lead_index, lead in enumerate(leads, start=1):
        score = score_lead(lead)
        if queries.lead_status_for(score, lead.status) == "qualified":
            qualified_count += 1
        raw_ids = [
            raw_record_ids_by_url[record.source_url]
            for record in lead.source_records
            if record.source_url in raw_record_ids_by_url
        ]
        queries.insert_lead_with_score(connection, job_id, lead, raw_ids, score)
        queries.update_job_progress(
            connection,
            job_id,
            leads_created=lead_index,
            qualified_leads=qualified_count,
        )

    queries.mark_job_completed(
        connection,
        job_id,
        records_found=len(raw_records),
        leads_created=len(leads),
        qualified_leads=qualified_count,
    )


def fetch_parse_and_store_records(
    connection: Connection,
    job_id: Any,
    source_urls: list[SourceUrl],
) -> tuple[list[ParsedSourceRecord], dict[str, Any]]:
    raw_records: list[ParsedSourceRecord] = []
    raw_record_ids_by_url: dict[str, Any] = {}
    for source_url in source_urls:
        record = fetch_and_parse(source_url)
        raw_records.append(record)
        raw_record_ids_by_url[record.source_url] = queries.insert_raw_record(
            connection,
            job_id,
            record,
        )
        queries.update_job_progress(connection, job_id, records_found=len(raw_records))
    return raw_records, raw_record_ids_by_url


def collect_job_source_urls(job: dict[str, Any], provider: SerpProvider) -> SourceUrlCollection:
    return collect_source_url_details(
        industry=job["industry"],
        location=job["location"],
        selected_sources=list(job.get("selected_sources") or []),
        target_record_count=job.get("target_record_count") or 500,
        provider=provider,
    )


def log_collection_requests(
    connection: Connection,
    job_id: Any,
    request_logs: list[SerpRequestLog],
) -> None:
    for request_log in request_logs:
        queries.log_api_request(
            connection,
            search_job_id=job_id,
            provider=request_log.provider,
            endpoint=request_log.endpoint,
            query=request_log.query,
            request_type="serp_search",
            status_code=request_log.status_code,
            success=request_log.success,
            credits_used=request_log.credits_used,
            estimated_cost=request_log.estimated_cost,
            error_message=request_log.error_message,
            metadata={"source_name": request_log.source_name},
        )


def fail_if_all_searches_failed(collection: SourceUrlCollection) -> None:
    if collection.request_logs and not any(log.success for log in collection.request_logs):
        raise RuntimeError("All SERP searches failed; see api_request_logs for details")
