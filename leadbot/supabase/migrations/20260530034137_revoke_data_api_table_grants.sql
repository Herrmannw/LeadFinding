-- V1 uses server-side direct Postgres access from Next.js and the Python worker.
-- Keep RLS enabled but leave anon/authenticated without table policies so the
-- Supabase Data API is denied by default until an explicit auth model exists.
revoke all on table public.search_jobs from anon, authenticated;
revoke all on table public.raw_source_records from anon, authenticated;
revoke all on table public.leads from anon, authenticated;
revoke all on table public.lead_sources from anon, authenticated;
revoke all on table public.lead_scores from anon, authenticated;
revoke all on table public.api_request_logs from anon, authenticated;
