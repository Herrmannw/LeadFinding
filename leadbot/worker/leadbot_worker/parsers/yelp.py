from __future__ import annotations

from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.parsers.common import (
    find_phone,
    first_json_ld_value,
    first_text,
    json_ld_objects,
    meta_content,
    soup_for,
)

PARSER_VERSION = "yelp_v1"


def parse_yelp_page(html: str, source_url: str, query_used: str | None = None) -> ParsedSourceRecord:
    try:
        soup = soup_for(html)
        json_ld = json_ld_objects(soup)
        name = first_json_ld_value(json_ld, ["name"]) or first_text(soup, ["h1"])
        description = meta_content(soup, ['meta[name="description"]', 'meta[property="og:description"]'])
        page_text = soup.get_text(" ", strip=True)
        phone = first_json_ld_value(json_ld, ["telephone"]) or find_phone(page_text)
        rating_value = _rating_value(first_json_ld_value(json_ld, ["aggregateRating"]))
        review_count = _review_count(first_json_ld_value(json_ld, ["aggregateRating"]))

        confidence = 0.45
        if name:
            confidence += 0.25
        if phone:
            confidence += 0.15
        if rating_value or review_count:
            confidence += 0.1

        return ParsedSourceRecord(
            source_name="yelp",
            source_url=source_url,
            query_used=query_used,
            business_name=name,
            phone=phone,
            category=first_json_ld_value(json_ld, ["servesCuisine"]) or None,
            rating=rating_value,
            review_count=review_count,
            profile_text=description,
            raw_payload={"json_ld_count": len(json_ld)},
            parse_status="parsed" if name else "partial",
            parse_confidence=min(confidence, 1.0),
            parser_version=PARSER_VERSION,
        )
    except Exception as exc:  # noqa: BLE001 - parser failures must be stored, not crash jobs.
        return ParsedSourceRecord(
            source_name="yelp",
            source_url=source_url,
            query_used=query_used,
            parse_status="failed",
            parse_confidence=0,
            parser_version=PARSER_VERSION,
            error_message=str(exc),
        )


def _rating_value(value: object) -> float | None:
    if isinstance(value, dict) and value.get("ratingValue") is not None:
        return float(value["ratingValue"])
    return None


def _review_count(value: object) -> int | None:
    if isinstance(value, dict):
        count = value.get("reviewCount") or value.get("ratingCount")
        if count is not None:
            return int(count)
    return None
