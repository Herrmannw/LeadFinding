from __future__ import annotations

from leadbot_worker.models.lead import LeadCandidate, WebsiteStatus
from leadbot_worker.models.raw_record import ParsedSourceRecord

USABLE_PARSE_STATUSES = {"parsed", "partial"}
LOW_PARSE_CONFIDENCE_THRESHOLD = 0.5


def classify_website_status(lead: LeadCandidate) -> WebsiteStatus:
    if lead.website_url:
        return "website_found"
    if not lead.source_records:
        return "unknown"

    usable_records = [record for record in lead.source_records if is_usable_website_evidence(record)]
    if any(record.website_url for record in usable_records):
        return "website_found"
    if not usable_records:
        return "unknown"
    if len(usable_records) == len(lead.source_records):
        return "no_website_found"
    return "unclear"


def is_usable_website_evidence(record: ParsedSourceRecord) -> bool:
    if record.parse_status not in USABLE_PARSE_STATUSES:
        return False
    return not is_low_confidence(record)


def is_low_confidence(record: ParsedSourceRecord) -> bool:
    return (
        record.parse_confidence is not None
        and record.parse_confidence < LOW_PARSE_CONFIDENCE_THRESHOLD
    )
