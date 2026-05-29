# LeadBot V1 System Architecture

## Recommended Tech Stack

Frontend:
- Next.js
- React
- shadcn/ui or simple table components
- Supabase JS client

Database:
- Supabase Postgres

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
- Allow filtering/sorting
- Maybe allow CSV export

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
