# Agentic Workflow Task Plan

Use this file to guide coding agents through the build.

## Global Rules for Agents

- Keep V1 small.
- Do not add HubSpot integration.
- Do not build outreach/email automation.
- Do not scrape Google Maps.
- Do not store raw HTML by default.
- Use raw source records first, then canonical leads.
- Preserve source evidence.
- Write simple, readable code.
- Prefer boring architecture over clever abstractions.
- Do not introduce Prisma/tRPC unless the project direction changes to full TypeScript.
- Do not introduce browser-side Supabase table access in V1.
- Keep `DATABASE_URL` server-only.
- Keep RLS enabled and deny `anon`/`authenticated` table access unless an explicit auth architecture change adds ownership columns and policies.
- Python worker is responsible for scraping, parsing, dedupe, and scoring.
- Next.js frontend is responsible for creating jobs and displaying results.

---

# Milestone 1: Database Schema

Goal:
Create the Supabase/Postgres schema for V1.

Tasks:
1. Create SQL migration file.
2. Add tables:
   - search_jobs
   - raw_source_records
   - leads
   - lead_sources
   - lead_scores
   - api_request_logs
3. Add useful indexes.
4. Add status fields as text for now.
5. Do not create source_configs yet unless needed.
6. Do not add HubSpot fields yet.

Acceptance criteria:
- Migration runs cleanly.
- Tables exist.
- Basic insert/select works.
- Foreign keys are valid.

---

# Milestone 2: Frontend Search Form

Goal:
Create a simple UI for creating search jobs.

Fields:
- industry/search term
- location
- target record count
- source checkboxes:
  - Yelp
  - Thumbtack

Tasks:
1. Create form.
2. Validate required fields.
3. Insert row into `search_jobs`.
4. Set status to `queued`.
5. Redirect/show job detail page.
6. Display job status/progress.

Acceptance criteria:
- User can create a search job from the browser.
- Job appears in database.
- Job status is visible.

Current status:
- Implemented.
- Uses Next.js server actions and server-only direct Postgres access.
- Job progress is displayed on page load/manual refresh; realtime or polling refresh is not part of Milestone 2.

---

# Milestone 3: Python Worker Skeleton

Goal:
Create a Python worker that polls queued jobs.

Tasks:
1. Connect Python to Supabase/Postgres.
2. Poll `search_jobs` where status = `queued`.
3. Mark job `running`.
4. Simulate processing.
5. Mark job `completed`.
6. Handle errors and mark job `failed`.

Acceptance criteria:
- Worker can pick up a queued job.
- Status changes from queued → running → completed.
- Errors are stored in `error_message`.

Current status:
- Implemented.
- Default worker mode is `simulate`, which claims one queued job and marks it completed without running scraper/parser stages.
- Use `--mode pipeline` only when working on later milestones.
- Unit tests cover empty queues, successful job execution, and failed runner error persistence.

---

# Milestone 4: SERP URL Collection

Goal:
Generate Yelp/Thumbtack search queries and collect result URLs.

Tasks:
1. Define hardcoded source configs in Python.
2. Generate queries from industry/location.
3. Call selected SERP provider or mock provider.
4. Log each API call to `api_request_logs`.
5. Filter URLs by source domain.
6. Dedupe URLs.
7. Save URLs for parsing.

Acceptance criteria:
- Worker can collect Yelp/Thumbtack URLs for a search job.
- API usage is logged.
- Duplicate URLs are removed.

Current status:
- Implemented as `leadbot-worker --once --mode collect-urls`.
- Discovered source URLs are stored in `raw_source_records` with `parse_status = 'needs_review'`.
- Parser, dedupe, website-status, and scoring work remains Milestone 5+ even though scaffold code exists.

---

# Milestone 5: Source Parsers

Goal:
Parse Yelp and Thumbtack pages into a common raw record shape.

Tasks:
1. Create Pydantic model for raw parser output.
2. Implement `parse_yelp_page`.
3. Implement `parse_thumbtack_page`.
4. Save parsed output to `raw_source_records`.
5. Include `parse_confidence`.
6. Include `raw_payload` for source-specific fields.

Acceptance criteria:
- Yelp page produces raw record.
- Thumbtack page produces raw record.
- Missing fields are allowed.
- Parser failures are stored as failed/partial records.

Current status:
- Implemented as `leadbot-worker --once --mode parse-pages`.
- Parser tests cover fixture-based Yelp and Thumbtack extraction, partial records, and unknown-parser failure.
- The parser code does not require real SERP results; live pages should be used later for smoke testing and fixture expansion.

---

# Milestone 6: Normalization and Dedupe

Goal:
Turn raw records into canonical leads.

Tasks:
1. Normalize names.
2. Normalize phone numbers.
3. Normalize website domains.
4. Group records using:
   - same phone
   - same website domain
   - same address
   - fuzzy name + city
5. Create/update `leads`.
6. Create `lead_sources` links.

Acceptance criteria:
- Duplicate Yelp/Thumbtack records can merge into one lead.
- Source evidence is preserved.
- Uncertain duplicates can be marked `needs_review`.

---

# Milestone 7: Website Presence Check

Goal:
Identify businesses that likely do not have their own website.

Tasks:
1. Check whether source profiles expose a website URL.
2. If no website URL, optionally run a web search for:
   - business name + city/state
   - business name + phone
3. Classify website status:
   - no_website_found
   - website_found
   - broken_website
   - parked_domain
   - unclear
4. Save status on `leads`.

Acceptance criteria:
- Leads get a website status.
- No-website leads are distinguishable from unknown/unclear leads.

---

# Milestone 8: Scoring

Goal:
Score leads for alive/no-website/opportunity.

Tasks:
1. Implement alive score.
2. Implement no-website score.
3. Implement opportunity score.
4. Save score record to `lead_scores`.
5. Copy latest scores onto `leads`.
6. Include score reasons.

Acceptance criteria:
- Each lead receives scores.
- Each score includes human-readable reasons.
- High-priority leads can be sorted in frontend.

---

# Milestone 9: Dashboard

Goal:
Display ranked leads.

Columns:
- business name
- category
- city/state
- phone
- sources found
- website status
- alive score
- no-website score
- opportunity score
- score reasons
- source links
- status

Tasks:
1. Build table.
2. Add filters:
   - source
   - website status
   - status
   - minimum opportunity score
3. Add sort by opportunity score.
4. Add simple export if easy.

Acceptance criteria:
- User can view top leads for a job.
- User can understand why a lead was scored highly.

---

# Milestone 10: Cleanup and Reliability

Goal:
Make V1 usable.

Tasks:
1. Add basic retry handling.
2. Add rate limiting.
3. Add API quota guard.
4. Add duplicate URL checks.
5. Add parser error logging.
6. Add simple tests for normalization and scoring.

Acceptance criteria:
- Worker does not crash on bad pages.
- API usage is visible.
- Parser failures do not break the job.
