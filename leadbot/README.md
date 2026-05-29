# LeadBot V1

LeadBot V1 finds local service businesses from marketplace sources, stores raw source records, dedupes them into canonical leads, and scores likely no-website opportunities.

Implemented so far:

- Supabase/Postgres migration for the V1 tables.
- Python worker package with queue polling, mock/SerpAPI URL collection, parser contracts, raw record persistence, dedupe, website status classification, and scoring.
- Unit tests for URL collection, normalization, dedupe, and scoring.

Next milestone:

- Add the Next.js frontend for creating `search_jobs` and viewing ranked leads.
