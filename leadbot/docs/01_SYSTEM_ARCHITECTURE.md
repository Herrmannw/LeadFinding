# LeadBot V1 System Architecture

## Recommended Tech Stack

Frontend:
- Next.js
- React
- shadcn/ui or simple table components
- Server actions/pages with server-only Postgres access

Database:
- Supabase Postgres
- Row Level Security enabled on public tables
- No browser/Data API access in V1

Worker/Scraper:
- Python
- httpx for HTTP requests
- BeautifulSoup, lxml, or selectolax for parsing
- Playwright only when necessary
- Pydantic for parser output validation
- rapidfuzz for dedupe
- psycopg, SQLAlchemy Core, or SQLModel for database writes

Queue:
- V1: simple polling worker or cron-style worker
- Later: Redis + RQ
- Much later: Celery if needed

## Architecture Decision: Database Access

V1 uses Supabase as hosted Postgres, not as a browser-facing data API.

The Next.js frontend reads and writes database rows only from server-side code using `DATABASE_URL`. The Python worker also connects directly to Postgres with `DATABASE_URL`. Do not add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, or browser-side Supabase table access for V1.

Why:
- The app is an internal tool with no V1 multi-user/team ownership model.
- Server actions are already the application boundary for validation and mutations.
- The worker needs direct database access for queue claiming, progress updates, and pipeline writes.
- Avoiding browser table access keeps the RLS model simple until real auth requirements exist.

If a later milestone needs Supabase Auth, Realtime, mobile clients, or direct browser reads/writes, make that an explicit architecture change first. That change must add an ownership model such as `owner_user_id` or `account_id`, write matching RLS policies, and migrate frontend data access intentionally.

## RLS and Policy Model

All V1 tables live in the `public` schema, so RLS stays enabled as defense in depth for Supabase's exposed schema defaults.

Current V1 policy:
- No `anon` policies.
- No `authenticated` policies.
- No browser/client table access.
- Server-side Next.js and the Python worker use private `DATABASE_URL` connections.

This means the Supabase Data API should not be able to read or mutate these tables with `anon` or `authenticated` JWTs. That is intentional. Do not add broad policies like `using (true)` unless the app has deliberately switched to a Supabase Auth/Data API access model.

## High-Level Data Flow

```text
Frontend search form
→ search_jobs row
→ Python worker picks up queued job
→ Google/SERP source URL collection
→ raw_source_records rows
→ parser/normalizer
→ leads rows
→ lead_sources links raw records to leads
→ scoring program creates lead_scores
→ frontend displays ranked leads
```

## Why Store Raw Records Separately From Leads?

A raw source record is one scraped/listed result from Yelp or Thumbtack.

A lead is one real-world business after cleaning and dedupe.

Example:

```text
Yelp: ABC Heating & Air
Thumbtack: ABC HVAC Services
```

These may become one canonical lead.

Do not write scraped records directly into the `leads` table. Scraped data is messy and can contain duplicates, bad parses, partial records, or irrelevant pages.

## Job-Based Processing

The frontend should not scrape 500 records inside a single web request.

Instead:

1. User submits search.
2. App creates `search_jobs` row with status `queued`.
3. Worker finds queued jobs.
4. Worker updates job status to `running`.
5. Worker stores raw records as they are found.
6. Worker updates progress counts.
7. Worker marks job `completed` or `failed`.

## V1 Components

### Frontend

Responsibilities:
- Render search form
- Create search job
- Show job progress
- Show lead table
- Later: allow filtering/sorting
- Later: maybe allow CSV export

### Python Worker

Responsibilities:
- Pick up queued jobs
- Generate search queries
- Call SERP/Google search API
- Collect source URLs
- Fetch source pages
- Parse source pages
- Save raw records
- Normalize and dedupe
- Score leads
- Update job status

### Database

Responsibilities:
- Persist jobs
- Persist raw source records
- Persist canonical leads
- Persist source-to-lead evidence
- Persist score history
- Persist API usage logs

## Search Source Strategy

For V1, source selection means enabling Google/SERP site search patterns.

Example:

```text
Yelp selected:
site:yelp.com/biz "{industry}" "{location}"

Thumbtack selected:
site:thumbtack.com "{industry}" "{location}"
```

The system should then send discovered source URLs to the correct parser.

## Hardcoded Source Configs for V1

For V1, it is acceptable to hardcode source configs in code.

Example:

```python
SOURCES = {
    "yelp": {
        "domain": "yelp.com",
        "query_templates": [
            'site:yelp.com/biz "{industry}" "{location}"'
        ],
        "parser": "yelp_parser",
    },
    "thumbtack": {
        "domain": "thumbtack.com",
        "query_templates": [
            'site:thumbtack.com "{industry}" "{location}"'
        ],
        "parser": "thumbtack_parser",
    },
}
```

A `source_configs` table can be added later if source management becomes annoying.

## Do Not Overbuild V1

Avoid:
- full microservice architecture
- Kafka
- Kubernetes
- complex auth
- HubSpot sync
- autonomous outreach
- raw HTML storage
- 10 different lead sources
- Google Maps scraping
