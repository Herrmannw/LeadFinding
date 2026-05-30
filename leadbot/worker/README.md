# LeadBot Worker

Python worker for the V1 pipeline described in `../docs`.

## Environment

Set `DATABASE_URL` to a Supabase/Postgres connection string.

The worker uses direct server-side Postgres access. It does not rely on Supabase Data API policies.

Optional:

- `LEADBOT_SERP_PROVIDER=mock` uses deterministic mock URLs.
- `LEADBOT_SERP_PROVIDER=serpapi` uses SerpAPI.
- `SERPAPI_API_KEY` is required for SerpAPI.

## Run

```bash
pip install -e ".[dev]"
leadbot-worker --once
```

The first implementation includes the queue loop, source config, URL collection, parser contracts, normalization, dedupe, website status classification, and scoring. Real page fetching and parser selectors are intentionally conservative and can be strengthened source-by-source.
