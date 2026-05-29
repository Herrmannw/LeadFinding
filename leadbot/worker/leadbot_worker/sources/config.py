from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceConfig:
    name: str
    domain: str
    query_templates: tuple[str, ...]


SOURCES: dict[str, SourceConfig] = {
    "yelp": SourceConfig(
        name="yelp",
        domain="yelp.com",
        query_templates=('site:yelp.com/biz "{industry}" "{location}"',),
    ),
    "thumbtack": SourceConfig(
        name="thumbtack",
        domain="thumbtack.com",
        query_templates=('site:thumbtack.com "{industry}" "{location}"',),
    ),
}


def selected_source_configs(selected_sources: list[str]) -> list[SourceConfig]:
    if not selected_sources:
        return list(SOURCES.values())

    configs: list[SourceConfig] = []
    for source_name in selected_sources:
        config = SOURCES.get(source_name)
        if config is None:
            valid_sources = ", ".join(sorted(SOURCES))
            raise ValueError(f"Unknown source {source_name!r}; expected one of: {valid_sources}")
        configs.append(config)
    return configs


def build_queries(
    industry: str,
    location: str,
    selected_sources: list[str],
) -> list[tuple[str, SourceConfig]]:
    queries: list[tuple[str, SourceConfig]] = []
    for config in selected_source_configs(selected_sources):
        for template in config.query_templates:
            queries.append((template.format(industry=industry, location=location), config))
    return queries
