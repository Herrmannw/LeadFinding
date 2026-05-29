# LeadBot Coding Guidelines

## General Principles

- Build the smallest useful version first.
- Keep pipeline stages explicit.
- Store raw source records before canonical leads.
- Do not over-optimize early.
- Do not build a scraping platform; build a focused lead discovery tool.
- Prefer readable code over clever abstractions.
- Every external API call should be logged.
- Every score should include reasons.

## Project Structure Recommendation

```text
leadbot/
  frontend/
    app/
    components/
    lib/
  worker/
    leadbot_worker/
      sources/
        yelp.py
        thumbtack.py
      parsers/
        yelp.py
        thumbtack.py
      pipeline/
        collect_urls.py
        parse_records.py
        normalize.py
        dedupe.py
        website_presence.py
        score.py
      db/
        connection.py
        queries.py
      models/
        raw_record.py
        lead.py
        score.py
      main.py
  supabase/
    migrations/
      001_initial_schema.sql
  docs/
    00_PROJECT_OVERVIEW.md
    01_SYSTEM_ARCHITECTURE.md
    02_DATABASE_SCHEMA.md
    03_PIPELINE_AND_SCORING.md
    04_AGENT_TASKS.md
    05_CODING_GUIDELINES.md
```

## Python Worker Guidelines

Use:
- Pydantic for parser output models
- httpx for HTTP
- BeautifulSoup/selectolax for parsing
- Playwright only as fallback
- rapidfuzz for fuzzy matching
- plain SQL, psycopg, SQLAlchemy Core, or SQLModel for DB writes

Avoid:
- scraping in frontend code
- long-running web requests
- storing raw HTML by default
- complicated queue systems before needed
- Selenium unless Playwright is insufficient

## Parser Contract

Each parser should return the same shape.

Example model:

```python
class ParsedSourceRecord(BaseModel):
    source_name: str
    source_url: str
    business_name: str | None = None
    phone: str | None = None
    website_url: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    category: str | None = None
    rating: float | None = None
    review_count: int | None = None
    profile_text: str | None = None
    raw_payload: dict = {}
    parse_confidence: float | None = None
```

A parser should never crash the job. If parsing fails, save a failed or partial raw record.

## Database Write Rules

- Insert every parsed source result into `raw_source_records`.
- Never skip raw storage just because dedupe found an existing lead.
- Link raw records to leads using `lead_sources`.
- Keep latest scores on `leads` for easy sorting.
- Keep score history in `lead_scores`.

## Dedupe Rules

Use this order:

```text
1. same phone
2. same website domain
3. same exact address
4. fuzzy name + same city
5. fuzzy name + same category + same city
```

Do not merge low-confidence duplicates automatically. Mark them `needs_review`.

## API Usage Rules

Every external API call should create an `api_request_logs` row.

Log:
- provider
- endpoint
- query
- request type
- status code
- success/failure
- credits used
- estimated cost
- error message

Before making requests, check quota/budget if configured.

## Scoring Rules

Keep three scores:
- `alive_score`
- `no_website_score`
- `opportunity_score`

Every score run should produce:
- numeric scores
- score version
- reasons
- recommended bucket

Do not score raw records. Score canonical leads after dedupe.

## Compliance / Risk Rules

- Focus on public business information.
- Do not scrape private/login-only data.
- Do not bypass CAPTCHAs.
- Do not build anti-bot evasion systems.
- Rate limit requests.
- Cache results.
- Respect site restrictions where applicable.
- Do not store sensitive personal data unnecessarily.

## V1 Non-Goals

Do not implement:
- HubSpot sync
- email outreach
- autonomous agents
- Google Maps scraping
- full CRM
- multi-user/team roles unless trivial
- source config admin UI
- advanced AI lead writing
- raw HTML archive
