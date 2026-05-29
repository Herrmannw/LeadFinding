from __future__ import annotations

from typing import Any

from psycopg import Connection

from leadbot_worker.db import queries
from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.collect_urls import SerpProvider, collect_source_url_details
from leadbot_worker.pipeline.dedupe import dedupe_records
from leadbot_worker.pipeline.parse_records import fetch_and_parse
from leadbot_worker.pipeline.score import score_lead


def run_search_job(connection: Connection, job: dict[str, Any], provider: SerpProvider) -> bool:
    job_id = job["id"]
    selected_sources = list(job.get("selected_sources") or [])

    try:
        collection = collect_source_url_details(
            industry=job["industry"],
            location=job["location"],
            selected_sources=selected_sources,
            target_record_count=job.get("target_record_count") or 500,
            provider=provider,
        )
        for request_log in collection.request_logs:
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
        if collection.request_logs and not any(log.success for log in collection.request_logs):
            raise RuntimeError("All SERP searches failed; see api_request_logs for details")

        raw_records: list[ParsedSourceRecord] = []
        raw_record_ids_by_url: dict[str, Any] = {}
        for source_url in collection.urls:
            record = fetch_and_parse(source_url)
            raw_records.append(record)
            raw_record_ids_by_url[record.source_url] = queries.insert_raw_record(
                connection,
                job_id,
                record,
            )
            queries.update_job_progress(connection, job_id, records_found=len(raw_records))

        parsed_records = [record for record in raw_records if record.parse_status != "failed"]
        leads = dedupe_records(parsed_records)
        qualified_count = 0

        for lead_index, lead in enumerate(leads, start=1):
            score = score_lead(lead)
            if score.recommended_bucket == "high_priority":
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
        return True
    except Exception as exc:  # noqa: BLE001 - jobs should fail cleanly with stored message.
        queries.mark_job_failed(connection, job_id, str(exc))
        return False
