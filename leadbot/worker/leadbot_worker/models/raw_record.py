from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

ParseStatus = Literal["parsed", "partial", "failed", "needs_review"]


class ParsedSourceRecord(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_name: str
    source_url: str
    query_used: str | None = None
    business_name: str | None = None
    phone: str | None = None
    website_url: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    category: str | None = None
    rating: float | None = None
    review_count: int | None = None
    profile_text: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    parse_status: ParseStatus = "parsed"
    parse_confidence: float | None = None
    parser_version: str | None = None
    error_message: str | None = None


class SourceUrl(BaseModel):
    source_name: str
    url: HttpUrl
    query_used: str
