from __future__ import annotations

import httpx

from leadbot_worker.models.raw_record import ParsedSourceRecord, SourceUrl
from leadbot_worker.parsers.thumbtack import parse_thumbtack_page
from leadbot_worker.parsers.yelp import parse_yelp_page


def fetch_and_parse(source_url: SourceUrl) -> ParsedSourceRecord:
    try:
        response = httpx.get(str(source_url.url), timeout=30, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - network failures become failed raw records.
        return ParsedSourceRecord(
            source_name=source_url.source_name,
            source_url=str(source_url.url),
            query_used=source_url.query_used,
            parse_status="failed",
            parse_confidence=0,
            error_message=str(exc),
        )

    return parse_html(source_url.source_name, response.text, str(source_url.url), source_url.query_used)


def parse_html(
    source_name: str,
    html: str,
    source_url: str,
    query_used: str | None = None,
) -> ParsedSourceRecord:
    if source_name == "yelp":
        return parse_yelp_page(html, source_url, query_used)
    if source_name == "thumbtack":
        return parse_thumbtack_page(html, source_url, query_used)
    return ParsedSourceRecord(
        source_name=source_name,
        source_url=source_url,
        query_used=query_used,
        parse_status="failed",
        parse_confidence=0,
        error_message=f"No parser configured for source {source_name}",
    )
