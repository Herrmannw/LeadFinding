# LeadBot V1

LeadBot V1 finds local service businesses from marketplace sources, stores raw source records, dedupes them into canonical leads, and scores likely no-website opportunities.

Current implementation status:

- Supabase/Postgres migration for the V1 tables.
- Milestone 2 frontend for creating `search_jobs` and viewing job status/ranked leads.
- Milestone 3 Python worker skeleton for queue polling and simulated job lifecycle.
- Milestone 4 worker mode for collecting, filtering, deduping, logging, and storing source URLs.
- Milestone 5 parser mode for fetching source pages and storing parsed raw records.
- Milestone 6 normalization/dedupe hardening for canonical leads and preserved source evidence.
- Later website-presence and scoring behavior exists as scaffold/in-progress, but Milestone 7+ should not be treated as complete yet.
- Unit tests exist for worker utilities, but later pipeline behavior still needs milestone-by-milestone hardening.
- Known Milestone 10 reliability bug: a worker crash after claiming a job can leave that job stuck in `running` until stale-job recovery is added.

Next milestone:

- Milestone 7: website presence checks.

Architecture decision:

- V1 uses server-only direct Postgres access from Next.js server actions/pages and the Python worker.
- V1 does not use the Supabase JS client in the browser or expose these tables through the Supabase Data API.
- RLS remains enabled on public tables, with no `anon`/`authenticated` policies, so accidental browser/Data API access is denied by default.
