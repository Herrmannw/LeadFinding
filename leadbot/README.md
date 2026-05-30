# LeadBot V1

LeadBot V1 finds local service businesses from marketplace sources, stores raw source records, dedupes them into canonical leads, and scores likely no-website opportunities.

Current implementation status:

- Supabase/Postgres migration for the V1 tables.
- Milestone 2 frontend for creating `search_jobs` and viewing job status/ranked leads.
- Python worker code exists as scaffold/in-progress for later milestones, but Milestone 3+ should not be treated as complete yet.
- Unit tests exist for worker utilities, but later pipeline behavior still needs milestone-by-milestone hardening.

Next milestone:

- Milestone 3: make the Python worker skeleton production-usable for queued jobs.

Architecture decision:

- V1 uses server-only direct Postgres access from Next.js server actions/pages and the Python worker.
- V1 does not use the Supabase JS client in the browser or expose these tables through the Supabase Data API.
- RLS remains enabled on public tables, with no `anon`/`authenticated` policies, so accidental browser/Data API access is denied by default.
