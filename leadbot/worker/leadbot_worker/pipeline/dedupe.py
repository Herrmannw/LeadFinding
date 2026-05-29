from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - dependency should exist in normal installs.
    fuzz = None

from leadbot_worker.models.lead import LeadCandidate
from leadbot_worker.models.raw_record import ParsedSourceRecord
from leadbot_worker.pipeline.normalize import (
    normalize_address,
    normalize_domain,
    normalize_name,
    normalize_phone,
)
from leadbot_worker.pipeline.website_presence import classify_website_status


def dedupe_records(records: list[ParsedSourceRecord]) -> list[LeadCandidate]:
    leads: list[LeadCandidate] = []
    for record in records:
        candidate = candidate_from_record(record)
        match_index, confidence = find_match(candidate, leads)
        if match_index is None:
            leads.append(candidate)
            continue
        leads[match_index] = merge_leads(leads[match_index], candidate, confidence)

    for index, lead in enumerate(leads):
        lead.website_status = classify_website_status(lead)
        lead.source_count = len(set(lead.sources_found))
        lead.dedupe_key = lead.dedupe_key or f"name:{lead.normalized_name or index}"
    return leads


def candidate_from_record(record: ParsedSourceRecord) -> LeadCandidate:
    normalized_name = normalize_name(record.business_name)
    phone = normalize_phone(record.phone)
    website_url = normalize_domain(record.website_url)
    address = normalize_address(record.address)
    sources_found = [record.source_name]

    if phone:
        dedupe_key = f"phone:{phone}"
        confidence = 1.0
    elif website_url:
        dedupe_key = f"domain:{website_url}"
        confidence = 1.0
    elif address:
        dedupe_key = f"address:{address}"
        confidence = 0.9
    else:
        dedupe_key = f"name:{normalized_name or record.source_url}"
        confidence = 0.65

    return LeadCandidate(
        canonical_name=record.business_name or record.source_url,
        normalized_name=normalized_name,
        phone=phone,
        website_url=website_url,
        address=record.address,
        city=record.city,
        state=record.state,
        category=record.category,
        sources_found=sources_found,
        source_count=1,
        best_source_url=record.source_url,
        dedupe_key=dedupe_key,
        dedupe_confidence=confidence,
        source_records=[record],
    )


def find_match(candidate: LeadCandidate, leads: list[LeadCandidate]) -> tuple[int | None, float]:
    candidate_domain = normalize_domain(candidate.website_url)
    candidate_address = normalize_address(candidate.address)

    for index, lead in enumerate(leads):
        if candidate.phone and candidate.phone == lead.phone:
            return index, 1.0
        if candidate_domain and candidate_domain == normalize_domain(lead.website_url):
            return index, 1.0
        if candidate_address and candidate_address == normalize_address(lead.address):
            return index, 0.9

    for index, lead in enumerate(leads):
        if not candidate.normalized_name or not lead.normalized_name:
            continue
        if not same_text(candidate.city, lead.city):
            continue
        similarity = name_similarity(candidate.normalized_name, lead.normalized_name)
        if similarity >= 90:
            return index, similarity / 100
        if similarity >= 80 and same_text(candidate.category, lead.category):
            return index, 0.8

    return None, 0


def merge_leads(existing: LeadCandidate, incoming: LeadCandidate, confidence: float) -> LeadCandidate:
    source_records = [*existing.source_records, *incoming.source_records]
    sources_found = sorted(set(existing.sources_found + incoming.sources_found))

    merged = replace(
        existing,
        canonical_name=prefer_text(existing.canonical_name, incoming.canonical_name),
        normalized_name=existing.normalized_name or incoming.normalized_name,
        phone=existing.phone or incoming.phone,
        website_url=existing.website_url or incoming.website_url,
        address=existing.address or incoming.address,
        city=existing.city or incoming.city,
        state=existing.state or incoming.state,
        category=existing.category or incoming.category,
        sources_found=sources_found,
        source_count=len(sources_found),
        best_source_url=existing.best_source_url or incoming.best_source_url,
        dedupe_confidence=max(existing.dedupe_confidence or 0, confidence),
        source_records=source_records,
    )
    return merged


def group_by_dedupe_key(records: list[ParsedSourceRecord]) -> dict[str, list[ParsedSourceRecord]]:
    grouped: dict[str, list[ParsedSourceRecord]] = defaultdict(list)
    for record in records:
        candidate = candidate_from_record(record)
        grouped[candidate.dedupe_key or record.source_url].append(record)
    return dict(grouped)


def name_similarity(left: str, right: str) -> int:
    if fuzz is not None:
        return int(max(fuzz.ratio(left, right), fuzz.token_set_ratio(left, right)))
    return 100 if left == right else 0


def same_text(left: str | None, right: str | None) -> bool:
    return (left or "").strip().lower() == (right or "").strip().lower()


def prefer_text(left: str, right: str) -> str:
    return left if len(left) >= len(right) else right
