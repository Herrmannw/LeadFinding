from __future__ import annotations

from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.normalize import normalize_phone
from leadbot_worker.parsers.common import (
    address_fields,
    city_state_from_text,
    clean_text,
    find_phone,
    first_json_ld_value,
    first_official_website_url,
    first_string_value,
    first_text,
    json_ld_objects,
    meta_content,
    parse_confidence,
    rating_value,
    review_count,
    soup_for,
)

PARSER_VERSION = "thumbtack_v1"


def parse_thumbtack_page(
    html: str,
    source_url: str,
    query_used: str | None = None,
) -> ParsedSourceRecord:
    try:
        soup = soup_for(html)
        json_ld = json_ld_objects(soup)
        name = first_string_value(
            first_json_ld_value(json_ld, ["name"]),
            first_text(soup, ["h1"]),
            meta_content(soup, ['meta[property="og:title"]']),
        )
        description = clean_text(
            meta_content(soup, ['meta[name="description"]', 'meta[property="og:description"]'])
        )
        page_text = soup.get_text(" ", strip=True)
        phone = first_string_value(
            first_json_ld_value(json_ld, ["telephone"]),
            first_text(soup, ['a[href^="tel:"]']),
            find_phone(page_text),
        )
        phone = normalize_phone(phone)
        website_url = first_official_website_url(
            soup,
            base_url=source_url,
            source_domains={"thumbtack.com"},
        )
        rating = rating_value(first_json_ld_value(json_ld, ["aggregateRating"]))
        reviews = review_count(first_json_ld_value(json_ld, ["aggregateRating"]))
        address, city, state = address_fields(first_json_ld_value(json_ld, ["address"]))
        if not address:
            address = first_text(soup, ["address", '[data-testid="pro-location"]'])
            city, state = city_state_from_text(address)
        category = first_string_value(
            first_json_ld_value(json_ld, ["category", "additionalType"]),
            first_text(
                soup,
                [
                    '[data-testid="pro-category"]',
                    'a[href*="/k/"]',
                    'a[href*="/central-air-conditioning"]',
                ],
            ),
        )

        confidence = parse_confidence(
            base=0.25,
            name=name,
            phone=phone,
            address=address,
            rating=rating,
            review_count_value=reviews,
            description=description,
            website_url=website_url,
        )

        return ParsedSourceRecord(
            source_name="thumbtack",
            source_url=source_url,
            query_used=query_used,
            business_name=name,
            phone=phone,
            website_url=website_url,
            address=address,
            city=city,
            state=state,
            category=category,
            rating=rating,
            review_count=reviews,
            profile_text=description,
            raw_payload={
                "json_ld_count": len(json_ld),
                "website_link_found": website_url is not None,
            },
            parse_status="parsed" if name else "partial",
            parse_confidence=confidence,
            parser_version=PARSER_VERSION,
        )
    except Exception as exc:  # noqa: BLE001 - parser failures must be stored, not crash jobs.
        return ParsedSourceRecord(
            source_name="thumbtack",
            source_url=source_url,
            query_used=query_used,
            parse_status="failed",
            parse_confidence=0,
            parser_version=PARSER_VERSION,
            error_message=str(exc),
        )
