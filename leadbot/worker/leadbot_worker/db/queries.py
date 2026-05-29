from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import Connection

from leadbot_worker.models.lead import LeadCandidate
from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.models.score import LeadScore


def claim_next_queued_job(connection: Connection) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            with next_job as (
              select id
              from search_jobs
              where status = 'queued'
              order by created_at
              limit 1
              for update skip locked
            )
            update search_jobs
            set status = 'running',
                started_at = coalesce(started_at, now()),
                finished_at = null,
                error_message = null
            from next_job
            where search_jobs.id = next_job.id
            returning search_jobs.*
            """
        )
        return cursor.fetchone()


def mark_job_completed(
    connection: Connection,
    job_id: UUID | str,
    records_found: int,
    leads_created: int,
    qualified_leads: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update search_jobs
            set status = 'completed',
                records_found = %s,
                leads_created = %s,
                qualified_leads = %s,
                error_message = null,
                finished_at = now()
            where id = %s
            """,
            (records_found, leads_created, qualified_leads, job_id),
        )


def mark_job_failed(connection: Connection, job_id: UUID | str, error_message: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update search_jobs
            set status = 'failed', error_message = %s, finished_at = now()
            where id = %s
            """,
            (error_message[:4000], job_id),
        )


def update_job_progress(
    connection: Connection,
    job_id: UUID | str,
    *,
    records_found: int | None = None,
    leads_created: int | None = None,
    qualified_leads: int | None = None,
) -> None:
    assignments: list[str] = []
    values: list[Any] = []
    if records_found is not None:
        assignments.append("records_found = %s")
        values.append(records_found)
    if leads_created is not None:
        assignments.append("leads_created = %s")
        values.append(leads_created)
    if qualified_leads is not None:
        assignments.append("qualified_leads = %s")
        values.append(qualified_leads)
    if not assignments:
        return

    values.append(job_id)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            update search_jobs
            set {", ".join(assignments)}
            where id = %s
            """,
            values,
        )


def log_api_request(
    connection: Connection,
    *,
    search_job_id: UUID | str,
    provider: str,
    endpoint: str | None,
    query: str | None,
    request_type: str,
    status_code: int | None,
    success: bool,
    credits_used: float = 0,
    estimated_cost: float | None = None,
    error_message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into api_request_logs (
                  search_job_id,
                  provider,
                  endpoint,
                  query,
                  request_type,
                  status_code,
                  success,
                  credits_used,
                  estimated_cost,
                  error_message,
                  metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    search_job_id,
                    provider,
                    endpoint,
                    query,
                    request_type,
                    status_code,
                    success,
                    credits_used,
                    estimated_cost,
                    error_message,
                    metadata or {},
                ),
            )
            if success:
                cursor.execute(
                    """
                    update search_jobs
                    set api_requests_used = api_requests_used + 1
                    where id = %s
                    """,
                    (search_job_id,),
                )


def insert_raw_record(
    connection: Connection,
    search_job_id: UUID | str,
    record: ParsedSourceRecord,
) -> UUID:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into raw_source_records (
              search_job_id,
              source_name,
              source_url,
              query_used,
              business_name,
              phone,
              website_url,
              address,
              city,
              state,
              category,
              rating,
              review_count,
              profile_text,
              raw_payload,
              parse_status,
              parse_confidence,
              parser_version,
              error_message
            )
            values (
              %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            on conflict (search_job_id, source_url) do update set
              business_name = excluded.business_name,
              phone = excluded.phone,
              website_url = excluded.website_url,
              address = excluded.address,
              city = excluded.city,
              state = excluded.state,
              category = excluded.category,
              rating = excluded.rating,
              review_count = excluded.review_count,
              profile_text = excluded.profile_text,
              raw_payload = excluded.raw_payload,
              parse_status = excluded.parse_status,
              parse_confidence = excluded.parse_confidence,
              parser_version = excluded.parser_version,
              error_message = excluded.error_message
            returning id
            """,
            (
                search_job_id,
                record.source_name,
                record.source_url,
                record.query_used,
                record.business_name,
                record.phone,
                record.website_url,
                record.address,
                record.city,
                record.state,
                record.category,
                record.rating,
                record.review_count,
                record.profile_text,
                record.raw_payload,
                record.parse_status,
                record.parse_confidence,
                record.parser_version,
                record.error_message,
            ),
        )
        row = cursor.fetchone()
        return row["id"]


def insert_lead_with_score(
    connection: Connection,
    search_job_id: UUID | str,
    lead: LeadCandidate,
    raw_record_ids: list[UUID],
    score: LeadScore,
) -> UUID:
    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into leads (
                  search_job_id,
                  canonical_name,
                  normalized_name,
                  phone,
                  website_url,
                  website_status,
                  address,
                  city,
                  state,
                  category,
                  sources_found,
                  source_count,
                  best_source_url,
                  alive_score,
                  no_website_score,
                  opportunity_score,
                  status,
                  dedupe_key,
                  dedupe_confidence
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                on conflict (search_job_id, dedupe_key) where dedupe_key is not null do update set
                  canonical_name = excluded.canonical_name,
                  normalized_name = excluded.normalized_name,
                  phone = excluded.phone,
                  website_url = excluded.website_url,
                  website_status = excluded.website_status,
                  address = excluded.address,
                  city = excluded.city,
                  state = excluded.state,
                  category = excluded.category,
                  sources_found = excluded.sources_found,
                  source_count = excluded.source_count,
                  best_source_url = excluded.best_source_url,
                  alive_score = excluded.alive_score,
                  no_website_score = excluded.no_website_score,
                  opportunity_score = excluded.opportunity_score,
                  status = excluded.status,
                  dedupe_confidence = excluded.dedupe_confidence
                returning id
                """,
                (
                    search_job_id,
                    lead.canonical_name,
                    lead.normalized_name,
                    lead.phone,
                    lead.website_url,
                    lead.website_status,
                    lead.address,
                    lead.city,
                    lead.state,
                    lead.category,
                    lead.sources_found,
                    lead.source_count,
                    lead.best_source_url,
                    score.alive_score,
                    score.no_website_score,
                    score.opportunity_score,
                    lead_status_for(score),
                    lead.dedupe_key,
                    lead.dedupe_confidence,
                ),
            )
            lead_id = cursor.fetchone()["id"]

            for record_id, record in zip(raw_record_ids, lead.source_records, strict=False):
                cursor.execute(
                    """
                    insert into lead_sources (
                      lead_id,
                      raw_source_record_id,
                      source_name,
                      source_url,
                      confidence
                    )
                    values (%s, %s, %s, %s, %s)
                    on conflict (lead_id, raw_source_record_id) do nothing
                    """,
                    (
                        lead_id,
                        record_id,
                        record.source_name,
                        record.source_url,
                        lead.dedupe_confidence,
                    ),
                )

            cursor.execute(
                """
                insert into lead_scores (
                  lead_id,
                  score_version,
                  alive_score,
                  no_website_score,
                  opportunity_score,
                  score_reasons,
                  recommended_bucket
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    lead_id,
                    score.score_version,
                    score.alive_score,
                    score.no_website_score,
                    score.opportunity_score,
                    score.score_reasons,
                    score.recommended_bucket,
                ),
            )
            return lead_id


def lead_status_for(score: LeadScore) -> str:
    if score.recommended_bucket == "high_priority":
        return "qualified"
    if score.recommended_bucket == "reject":
        return "rejected"
    return "new"
