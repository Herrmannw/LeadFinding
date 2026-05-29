create extension if not exists pgcrypto;

create table search_jobs (
  id uuid primary key default gen_random_uuid(),

  industry text not null,
  location text not null,
  target_record_count integer not null default 500 check (target_record_count > 0),

  selected_sources jsonb not null default '[]'::jsonb,

  status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
  records_found integer not null default 0,
  leads_created integer not null default 0,
  qualified_leads integer not null default 0,

  api_requests_used integer not null default 0,

  error_message text,

  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create table raw_source_records (
  id uuid primary key default gen_random_uuid(),

  search_job_id uuid not null references search_jobs(id) on delete cascade,

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

  parse_status text not null default 'parsed' check (parse_status in ('parsed', 'partial', 'failed', 'needs_review')),
  parse_confidence numeric,
  parser_version text,
  error_message text,

  scraped_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  unique(search_job_id, source_url)
);

create table leads (
  id uuid primary key default gen_random_uuid(),

  search_job_id uuid not null references search_jobs(id) on delete cascade,

  canonical_name text not null,
  normalized_name text,
  phone text,
  website_url text,

  website_status text not null default 'unknown' check (website_status in (
    'unknown',
    'no_website_found',
    'website_found',
    'broken_website',
    'parked_domain',
    'unclear'
  )),

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

  status text not null default 'new' check (status in (
    'new',
    'qualified',
    'needs_review',
    'duplicate',
    'rejected',
    'dead'
  )),

  dedupe_key text,
  duplicate_of_lead_id uuid references leads(id),
  dedupe_confidence numeric,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

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

create table lead_scores (
  id uuid primary key default gen_random_uuid(),

  lead_id uuid not null references leads(id) on delete cascade,

  score_version text not null,

  alive_score integer not null,
  no_website_score integer not null,
  opportunity_score integer not null,

  score_reasons jsonb not null default '[]'::jsonb,
  recommended_bucket text check (recommended_bucket in (
    'high_priority',
    'review',
    'low_priority',
    'reject'
  )),

  created_at timestamptz not null default now()
);

create table api_request_logs (
  id uuid primary key default gen_random_uuid(),

  search_job_id uuid references search_jobs(id) on delete set null,

  provider text not null,
  endpoint text,
  query text,
  request_type text not null,

  status_code integer,
  success boolean not null default false,
  credits_used numeric not null default 0,
  estimated_cost numeric,

  error_message text,
  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now()
);

create index search_jobs_status_created_at_idx on search_jobs(status, created_at);
create index raw_source_records_job_source_idx on raw_source_records(search_job_id, source_name);
create index raw_source_records_business_name_idx on raw_source_records(business_name);
create index raw_source_records_phone_idx on raw_source_records(phone);
create index leads_job_opportunity_idx on leads(search_job_id, opportunity_score desc nulls last);
create index leads_website_status_idx on leads(website_status);
create index leads_status_idx on leads(status);
create index leads_phone_idx on leads(phone) where phone is not null;
create index leads_dedupe_key_idx on leads(dedupe_key) where dedupe_key is not null;
create unique index leads_job_dedupe_key_unique_idx
on leads(search_job_id, dedupe_key)
where dedupe_key is not null;
create index lead_sources_lead_id_idx on lead_sources(lead_id);
create index lead_scores_lead_created_at_idx on lead_scores(lead_id, created_at desc);
create index api_request_logs_job_provider_idx on api_request_logs(search_job_id, provider);

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger leads_set_updated_at
before update on leads
for each row
execute function set_updated_at();

alter table search_jobs enable row level security;
alter table raw_source_records enable row level security;
alter table leads enable row level security;
alter table lead_sources enable row level security;
alter table lead_scores enable row level security;
alter table api_request_logs enable row level security;

create policy "authenticated can manage search jobs"
on search_jobs for all
to authenticated
using (true)
with check (true);

create policy "authenticated can manage raw source records"
on raw_source_records for all
to authenticated
using (true)
with check (true);

create policy "authenticated can manage leads"
on leads for all
to authenticated
using (true)
with check (true);

create policy "authenticated can manage lead sources"
on lead_sources for all
to authenticated
using (true)
with check (true);

create policy "authenticated can manage lead scores"
on lead_scores for all
to authenticated
using (true)
with check (true);

create policy "authenticated can manage api request logs"
on api_request_logs for all
to authenticated
using (true)
with check (true);
