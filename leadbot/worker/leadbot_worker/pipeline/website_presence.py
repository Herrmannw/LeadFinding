from __future__ import annotations

from leadbot_worker.models.lead import LeadCandidate, WebsiteStatus


def classify_website_status(lead: LeadCandidate) -> WebsiteStatus:
    if lead.website_url:
        return "website_found"
    if lead.source_records and all(not record.website_url for record in lead.source_records):
        return "no_website_found"
    return "unknown"
