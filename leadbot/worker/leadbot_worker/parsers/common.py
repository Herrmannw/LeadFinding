from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")


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
        if isinstance(loaded, dict):
            objects.append(loaded)
        elif isinstance(loaded, list):
            objects.extend(item for item in loaded if isinstance(item, dict))
    return objects


def first_json_ld_value(objects: list[dict[str, Any]], keys: list[str]) -> Any:
    for obj in objects:
        for key in keys:
            value = obj.get(key)
            if value:
                return value
    return None
