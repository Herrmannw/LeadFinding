drop policy if exists "authenticated can manage search jobs" on search_jobs;
drop policy if exists "authenticated can manage raw source records" on raw_source_records;
drop policy if exists "authenticated can manage leads" on leads;
drop policy if exists "authenticated can manage lead sources" on lead_sources;
drop policy if exists "authenticated can manage lead scores" on lead_scores;
drop policy if exists "authenticated can manage api request logs" on api_request_logs;

-- V1 uses server-side direct Postgres access from Next.js and the Python worker.
-- Keep RLS enabled but leave anon/authenticated without table policies so the
-- Supabase Data API is denied by default until an explicit auth model exists.
revoke all on table search_jobs from anon, authenticated;
revoke all on table raw_source_records from anon, authenticated;
revoke all on table leads from anon, authenticated;
revoke all on table lead_sources from anon, authenticated;
revoke all on table lead_scores from anon, authenticated;
revoke all on table api_request_logs from anon, authenticated;

create or replace function set_updated_at()
returns trigger
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create index if not exists lead_sources_raw_source_record_id_idx
on lead_sources(raw_source_record_id);

create index if not exists leads_duplicate_of_lead_id_idx
on leads(duplicate_of_lead_id)
where duplicate_of_lead_id is not null;
