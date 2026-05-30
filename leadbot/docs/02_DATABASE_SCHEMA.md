# LeadBot V1 Database Schema

## Tables Needed

V1 should use these core tables:

```text
search_jobs
raw_source_records
leads
lead_sources
lead_scores
api_request_logs
```

Optional later:

```text
source_configs
web_presence_checks
```

For V1, source configs can be hardcoded in code.

## Access Model

V1 uses Supabase Postgres through private server-side connections:

- Next.js server actions/pages use `DATABASE_URL`.
- The Python worker uses `DATABASE_URL`.
- Browser code does not use the Supabase JS client to access tables.
- The Supabase Data API is not part of the V1 application boundary.

Because these tables are in Supabase's default exposed `public` schema, every table should keep RLS enabled. The current V1 policy posture is deny-by-default for `anon` and `authenticated`: there are no table policies for those roles. This is intentional until the product has a real user/account ownership model.

Do not add broad `authenticated can manage everything` policies. If a future milestone introduces Supabase Auth or browser-side table access, first add ownership columns, define per-table policies, and update the frontend architecture intentionally.

---

# 1. `search_jobs`

Represents one user search request.

Example:

> Find HVAC businesses in Houston TX from Yelp and Thumbtack, with a best-effort goal of 500 records.

Fields:

```sql
create table search_jobs (
  id uuid primary key default gen_random_uuid(),

  industry text not null,
  location text not null,
  target_record_count integer default 500,

  selected_sources jsonb not null default '[]'::jsonb,

  status text not null default 'queued',
  records_found integer not null default 0,
  leads_created integer not null default 0,
  qualified_leads integer not null default 0,

  api_requests_used integer not null default 0,

  error_message text,

  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);
```

`target_record_count` is a best-effort goal for V1, not a guaranteed result count. The worker should stop once it reaches the goal, but SERP result availability, provider limits, selected sources, and duplicate filtering can produce fewer records.

Possible statuses:

```text
queued
running
completed
failed
cancelled
```

---

# 2. `raw_source_records`

Stores every parsed record from Yelp/Thumbtack before dedupe.

This is intentionally messy.

Fields:

```sql
create table raw_source_records (
  id uuid primary key default gen_random_uuid(),

  search_job_id uuid references search_jobs(id) on delete cascade,

  source_name text not null,
  source_url text not null,
  query_used text,

  business_name text,
  phone text,
  website_url text,
  address text,
  city text,
  state text,
  category text,
  rating numeric,
  review_count integer,
  profile_text text,

  raw_payload jsonb not null default '{}'::jsonb,

  parse_status text not null default 'parsed',
  parse_confidence numeric,
  parser_version text,
  error_message text,

  scraped_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  unique(search_job_id, source_url)
);
```

Possible parse statuses:

```text
parsed
partial
failed
needs_review
```

Notes:
- Do not store full raw HTML by default.
- Store source URL, extracted fields, parser version, confidence, and a small profile text excerpt.
- Use `raw_payload` for source-specific weird fields.

---

# 3. `leads`

Stores canonical deduped businesses.

One row should represent one real-world business.

Fields:

```sql
create table leads (
  id uuid primary key default gen_random_uuid(),

  canonical_name text not null,
  normalized_name text,
  phone text,
  website_url text,

  website_status text not null default 'unknown',

  address text,
  city text,
  state text,
  category text,

  sources_found jsonb not null default '[]'::jsonb,
  source_count integer not null default 0,
  best_source_url text,

  alive_score integer,
  no_website_score integer,
  opportunity_score integer,

  status text not null default 'new',

  dedupe_key text,
  duplicate_of_lead_id uuid references leads(id),
  dedupe_confidence numeric,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Possible `website_status` values:

```text
unknown
no_website_found
website_found
broken_website
parked_domain
unclear
```

Possible lead statuses:

```text
new
qualified
needs_review
duplicate
rejected
dead
```

---

# 4. `lead_sources`

Join table connecting canonical leads to raw records.

This preserves evidence for each lead.

Fields:

```sql
create table lead_sources (
  id uuid primary key default gen_random_uuid(),

  lead_id uuid not null references leads(id) on delete cascade,
  raw_source_record_id uuid not null references raw_source_records(id) on delete cascade,

  source_name text not null,
  source_url text not null,
  confidence numeric,

  created_at timestamptz not null default now(),

  unique(lead_id, raw_source_record_id)
);
```

Example:

```text
Lead: ABC Heating & Air
Sources:
- Yelp raw record
- Thumbtack raw record
```

---

# 5. `lead_scores`

Stores score history.

Keep this separate because the scoring formula will change.

Fields:

```sql
create table lead_scores (
  id uuid primary key default gen_random_uuid(),

  lead_id uuid not null references leads(id) on delete cascade,

  score_version text not null,

  alive_score integer not null,
  no_website_score integer not null,
  opportunity_score integer not null,

  score_reasons jsonb not null default '[]'::jsonb,
  recommended_bucket text,

  created_at timestamptz not null default now()
);
```

Example score reasons:

```json
[
  "Found on both Yelp and Thumbtack",
  "No official website found",
  "Has phone number",
  "Yelp profile has 34 reviews"
]
```

Recommended buckets:

```text
high_priority
review
low_priority
reject
```

---

# 6. `api_request_logs`

Tracks usage/cost for Google Custom Search, SerpAPI, etc.

Fields:

```sql
create table api_request_logs (
  id uuid primary key default gen_random_uuid(),

  search_job_id uuid references search_jobs(id) on delete set null,

  provider text not null,
  endpoint text,
  query text,
  request_type text,

  status_code integer,
  success boolean not null default false,

  credits_used numeric default 1,
  estimated_cost_cents numeric default 0,

  error_message text,

  requested_at timestamptz not null default now()
);
```

Example request types:

```text
search
page_fetch
website_check
```

---

## Suggested Indexes

```sql
create index idx_search_jobs_status on search_jobs(status);
create index idx_raw_source_records_job on raw_source_records(search_job_id);
create index idx_raw_source_records_source on raw_source_records(source_name);
create index idx_leads_status on leads(status);
create index idx_leads_scores on leads(opportunity_score, alive_score, no_website_score);
create index idx_leads_phone on leads(phone);
create index idx_leads_normalized_name_city on leads(normalized_name, city);
create index idx_api_request_logs_provider_date on api_request_logs(provider, requested_at);
```

## Design Principle

Use:

```text
raw_source_records = what was found
leads = what we believe is a real business
lead_sources = evidence linking them
lead_scores = why the lead is/is not valuable
```
