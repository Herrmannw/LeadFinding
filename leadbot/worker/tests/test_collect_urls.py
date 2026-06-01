from leadbot_worker.pipeline.collect_urls import (
    MockSerpProvider,
    SerpProvider,
    SerpSearchResult,
    collect_source_url_details,
    collect_source_urls,
)


def test_collect_source_urls_filters_selected_domains() -> None:
    urls = collect_source_urls(
        industry="HVAC",
        location="Houston TX",
        selected_sources=["yelp", "thumbtack"],
        target_record_count=10,
        provider=MockSerpProvider(),
    )

    assert {url.source_name for url in urls} == {"yelp", "thumbtack"}
    assert len({str(url.url) for url in urls}) == len(urls)


def test_collect_source_urls_queries_each_selected_source_before_trimming() -> None:
    collection = collect_source_url_details(
        industry="HVAC",
        location="Houston TX",
        selected_sources=["yelp", "thumbtack"],
        target_record_count=2,
        provider=MockSerpProvider(),
    )

    assert [log.source_name for log in collection.request_logs] == ["yelp", "thumbtack"]
    assert len(collection.urls) == 2
    assert {url.source_name for url in collection.urls} == {"yelp", "thumbtack"}


def test_collect_source_urls_defaults_empty_selection_to_all_sources() -> None:
    urls = collect_source_urls(
        industry="HVAC",
        location="Houston TX",
        selected_sources=[],
        target_record_count=10,
        provider=MockSerpProvider(),
    )

    assert {url.source_name for url in urls} == {"yelp", "thumbtack"}


class FailedSerpProvider(SerpProvider):
    name = "failed"
    endpoint = "https://example.test/search"

    def search(self, query: str, limit: int) -> SerpSearchResult:
        return SerpSearchResult(
            links=[],
            status_code=500,
            success=False,
            credits_used=1,
            error_message=f"failed query: {query}",
        )


def test_collect_source_url_details_records_failed_searches() -> None:
    collection = collect_source_url_details(
        industry="HVAC",
        location="Houston TX",
        selected_sources=["yelp"],
        target_record_count=10,
        provider=FailedSerpProvider(),
    )

    assert collection.urls == []
    assert len(collection.request_logs) == 1
    assert collection.request_logs[0].success is False
    assert collection.request_logs[0].status_code == 500
    assert collection.request_logs[0].credits_used == 1
