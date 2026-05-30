from __future__ import annotations

import re
from urllib.parse import urlparse

LEGAL_SUFFIX_RE = re.compile(r"\b(llc|inc|co|corp|corporation|company|ltd|pllc)\b", re.IGNORECASE)
PUNCT_RE = re.compile(r"[^a-z0-9\s]")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    normalized = name.lower().replace("&", " and ")
    normalized = LEGAL_SUFFIX_RE.sub(" ", normalized)
    normalized = PUNCT_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized or None


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    if len(digits) == 10:
        return digits
    return digits or None


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip().lower()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = parsed.netloc or parsed.path
    host = host.removeprefix("www.").rstrip("/")
    return host or None


def normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    normalized = address.lower()
    normalized = PUNCT_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized or None
