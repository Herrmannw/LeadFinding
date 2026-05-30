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

The default mode is the Milestone 3 skeleton:

```bash
leadbot-worker --once --mode simulate
```

It claims one queued job, marks it `running`, simulates processing, and marks it `completed`.

Later pipeline work can be exercised explicitly:

```bash
leadbot-worker --once --mode pipeline
```

Pipeline mode uses source config, URL collection, parser contracts, normalization, dedupe, website status classification, and scoring. Treat that path as Milestone 4+ work.
