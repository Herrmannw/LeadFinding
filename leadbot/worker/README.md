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
leadbot-worker --once --mode collect-urls
```

This is the Milestone 4 mode. It collects source URLs, logs SERP API requests, stores discovered URLs as `raw_source_records` with `parse_status = 'needs_review'`, and marks the job completed without running parser/dedupe/scoring stages.

Milestone 5 parser work can be exercised explicitly:

```bash
leadbot-worker --once --mode parse-pages
```

This collects source URLs, fetches the source pages, stores parsed Yelp/Thumbtack records in `raw_source_records`, and marks the job completed without running dedupe/scoring stages.

The later in-progress pipeline can be exercised explicitly:

```bash
leadbot-worker --once --mode pipeline
```

Pipeline mode uses source config, URL collection, parser contracts, normalization, dedupe, website status classification, and scoring. Treat that path as Milestone 6+ work.
