from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from leadbot_worker.models.raw_record import SourceUrl
from leadbot_worker.sources.config import SourceConfig, build_queries


class SerpProvider(ABC):
    name: str
    endpoint: str | None = None

    @abstractmethod
    def search(self, query: str, limit: int) -> "SerpSearchResult":
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class SerpSearchResult:
    links: list[str]
    status_code: int | None
    success: bool
    credits_used: float = 0
    estimated_cost: float | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class SerpRequestLog:
    provider: str
    endpoint: str | None
    query: str
    source_name: str
    status_code: int | None
    success: bool
    credits_used: float = 0
    estimated_cost: float | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class SourceUrlCollection:
    urls: list[SourceUrl] = field(default_factory=list)
    request_logs: list[SerpRequestLog] = field(default_factory=list)


class MockSerpProvider(SerpProvider):
    name = "mock"

    def search(self, query: str, limit: int) -> SerpSearchResult:
        if "yelp.com" in query:
            links = [
                "https://www.yelp.com/biz/example-heating-and-air-houston",
                "https://www.yelp.com/biz/lone-star-hvac-houston",
            ][:limit]
            return SerpSearchResult(links=links, status_code=200, success=True)
        if "thumbtack.com" in query:
            links = [
                "https://www.thumbtack.com/tx/houston/hvac/example-heating-and-air/service",
                "https://www.thumbtack.com/tx/houston/central-air-conditioning/lone-star-hvac/service",
            ][:limit]
            return SerpSearchResult(links=links, status_code=200, success=True)
        return SerpSearchResult(links=[], status_code=200, success=True)


class SerpApiProvider(SerpProvider):
    name = "serpapi"
    endpoint = "https://serpapi.com/search.json"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY is required when LEADBOT_SERP_PROVIDER=serpapi")

    def search(self, query: str, limit: int) -> SerpSearchResult:
        try:
            response = httpx.get(
                self.endpoint,
                params={"engine": "google", "q": query, "api_key": self.api_key, "num": limit},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            return SerpSearchResult(
                links=[],
                status_code=exc.response.status_code,
                success=False,
                credits_used=1,
                error_message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - request failures are logged and skipped.
            return SerpSearchResult(
                links=[],
                status_code=None,
                success=False,
                credits_used=0,
                error_message=str(exc),
            )

        results = payload.get("organic_results", [])
        links = [result["link"] for result in results if result.get("link")]
        return SerpSearchResult(
            links=links,
            status_code=response.status_code,
            success=True,
            credits_used=1,
        )


def provider_from_env() -> SerpProvider:
    provider_name = os.getenv("LEADBOT_SERP_PROVIDER", "mock").strip().lower()
    if provider_name == "serpapi":
        return SerpApiProvider()
    return MockSerpProvider()


def collect_source_urls(
    *,
    industry: str,
    location: str,
    selected_sources: list[str],
    target_record_count: int,
    provider: SerpProvider,
) -> list[SourceUrl]:
    return collect_source_url_details(
        industry=industry,
        location=location,
        selected_sources=selected_sources,
        target_record_count=target_record_count,
        provider=provider,
    ).urls


def collect_source_url_details(
    *,
    industry: str,
    location: str,
    selected_sources: list[str],
    target_record_count: int,
    provider: SerpProvider,
) -> SourceUrlCollection:
    per_query_limit = max(1, min(target_record_count, 100))
    discovered: list[SourceUrl] = []
    request_logs: list[SerpRequestLog] = []
    seen: set[str] = set()

    for query, source_config in build_queries(industry, location, selected_sources):
        result = provider.search(query, per_query_limit)
        request_logs.append(
            SerpRequestLog(
                provider=provider.name,
                endpoint=provider.endpoint,
                query=query,
                source_name=source_config.name,
                status_code=result.status_code,
                success=result.success,
                credits_used=result.credits_used,
                estimated_cost=result.estimated_cost,
                error_message=result.error_message,
            )
        )
        if not result.success:
            continue

        for url in result.links:
            normalized_url = normalize_source_url(url)
            if normalized_url in seen or not source_matches(normalized_url, source_config):
                continue
            if looks_like_search_page(normalized_url):
                continue
            seen.add(normalized_url)
            discovered.append(
                SourceUrl(source_name=source_config.name, url=normalized_url, query_used=query)
            )
    return SourceUrlCollection(
        urls=balance_source_urls(discovered, target_record_count),
        request_logs=request_logs,
    )


def balance_source_urls(urls: list[SourceUrl], limit: int) -> list[SourceUrl]:
    if len(urls) <= limit:
        return urls

    source_order: list[str] = []
    urls_by_source: dict[str, list[SourceUrl]] = {}
    for source_url in urls:
        if source_url.source_name not in urls_by_source:
            source_order.append(source_url.source_name)
            urls_by_source[source_url.source_name] = []
        urls_by_source[source_url.source_name].append(source_url)

    balanced: list[SourceUrl] = []
    offset = 0
    while len(balanced) < limit:
        added = False
        for source_name in source_order:
            source_urls = urls_by_source[source_name]
            if offset >= len(source_urls):
                continue
            balanced.append(source_urls[offset])
            added = True
            if len(balanced) >= limit:
                break
        if not added:
            break
        offset += 1
    return balanced


def normalize_source_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return f"https://{url}"
    return url.split("#", 1)[0].rstrip("/")


def source_matches(url: str, source_config: SourceConfig) -> bool:
    host = urlparse(url).netloc.lower()
    return host == source_config.domain or host.endswith(f".{source_config.domain}")


def looks_like_search_page(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(fragment in path for fragment in ["/search", "/categories", "/nearby"])
