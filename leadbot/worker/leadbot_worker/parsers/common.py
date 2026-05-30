from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
CITY_STATE_RE = re.compile(r"\b([A-Za-z][A-Za-z .'-]+),\s*([A-Z]{2})\b")
WHITESPACE_RE = re.compile(r"\s+")

NON_OWNED_WEBSITE_DOMAINS = {
    "angi.com",
    "facebook.com",
    "homeadvisor.com",
    "houzz.com",
    "instagram.com",
    "linkedin.com",
    "nextdoor.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "yelp.com",
    "youtube.com",
}


def soup_for(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def first_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            if text:
                return text
    return None


def first_attr(soup: BeautifulSoup, selectors: list[str], attr: str) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.get(attr):
            return clean_text(str(element[attr]))
    return None


def meta_content(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.get("content"):
            return str(element["content"]).strip()
    return None


def find_phone(text: str | None) -> str | None:
    if not text:
        return None
    match = PHONE_RE.search(text)
    return match.group(0) if match else None


def json_ld_objects(soup: BeautifulSoup) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            continue
        collect_json_ld_objects(loaded, objects)
    return objects


def collect_json_ld_objects(value: object, objects: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        objects.append(value)
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                collect_json_ld_objects(item, objects)
    elif isinstance(value, list):
        for item in value:
            collect_json_ld_objects(item, objects)


def first_json_ld_value(objects: list[dict[str, Any]], keys: list[str]) -> Any:
    for obj in objects:
        for key in keys:
            value = obj.get(key)
            if value:
                return value
    return None


def clean_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = WHITESPACE_RE.sub(" ", str(value)).strip()
    return text or None


def first_string_value(*values: object | None) -> str | None:
    for value in values:
        if isinstance(value, list):
            value = next((item for item in value if clean_text(item)), None)
        text = clean_text(value)
        if text:
            return text
    return None


def rating_value(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("ratingValue") or value.get("rating")
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def review_count(value: object) -> int | None:
    if isinstance(value, dict):
        value = value.get("reviewCount") or value.get("ratingCount")
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def address_fields(value: object) -> tuple[str | None, str | None, str | None]:
    if not isinstance(value, dict):
        return clean_text(value), None, None

    street = first_string_value(value.get("streetAddress"))
    city = first_string_value(value.get("addressLocality"))
    state = first_string_value(value.get("addressRegion"))
    postal_code = first_string_value(value.get("postalCode"))

    parts = [street, city, state_with_postal_code(state, postal_code)]
    address = ", ".join(part for part in parts if part)
    return address or None, city, state


def state_with_postal_code(state: str | None, postal_code: str | None) -> str | None:
    if state and postal_code:
        return f"{state} {postal_code}"
    return state or postal_code


def city_state_from_text(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    match = CITY_STATE_RE.search(text)
    if not match:
        return None, None
    return clean_text(match.group(1)), clean_text(match.group(2))


def first_official_website_url(
    soup: BeautifulSoup,
    *,
    base_url: str,
    source_domains: set[str],
) -> str | None:
    for link in soup.select("a[href]"):
        href = str(link.get("href") or "")
        candidate = clean_url(decode_redirect_url(href), base_url=base_url)
        if candidate and looks_like_official_website(candidate, source_domains):
            return candidate
    return None


def decode_redirect_url(href: str) -> str:
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    for key in ("url", "u"):
        values = query.get(key)
        if values:
            return unquote(values[0])
    return href


def clean_url(url: str | None, *, base_url: str) -> str | None:
    if not url:
        return None
    candidate = urljoin(base_url, url.strip())
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed._replace(fragment="", query="").geturl().rstrip("/")


def looks_like_official_website(url: str, source_domains: set[str]) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    blocked_domains = NON_OWNED_WEBSITE_DOMAINS | source_domains
    return not any(host == domain or host.endswith(f".{domain}") for domain in blocked_domains)


def parse_confidence(
    *,
    base: float,
    name: str | None,
    phone: str | None,
    address: str | None,
    rating: float | None,
    review_count_value: int | None,
    description: str | None,
    website_url: str | None,
) -> float:
    confidence = base
    if name:
        confidence += 0.25
    if phone:
        confidence += 0.15
    if address:
        confidence += 0.1
    if rating is not None or review_count_value is not None:
        confidence += 0.1
    if description:
        confidence += 0.05
    if website_url:
        confidence += 0.05
    return min(round(confidence, 3), 1.0)
