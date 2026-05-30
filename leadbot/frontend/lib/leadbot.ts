import { db } from "@/lib/db";

const ALLOWED_SOURCES = new Set(["yelp", "thumbtack"]);

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type SearchJob = {
  id: string;
  industry: string;
  location: string;
  target_record_count: number;
  selected_sources: string[];
  status: JobStatus;
  records_found: number;
  leads_created: number;
  qualified_leads: number;
  api_requests_used: number;
  error_message: string | null;
  created_at: Date;
  started_at: Date | null;
  finished_at: Date | null;
};

export type LeadRow = {
  id: string;
  canonical_name: string;
  phone: string | null;
  website_status: string;
  city: string | null;
  state: string | null;
  category: string | null;
  sources_found: string[];
  source_count: number;
  best_source_url: string | null;
  alive_score: number | null;
  no_website_score: number | null;
  opportunity_score: number | null;
  status: string;
};

type CreateSearchJobInput = {
  industry: string;
  location: string;
  targetRecordCount: number;
  selectedSources: string[];
};

export function normalizeSources(values: string[]) {
  const selected = values.filter((value) => ALLOWED_SOURCES.has(value));
  return selected.length > 0 ? selected : ["yelp", "thumbtack"];
}

export async function createSearchJob(input: CreateSearchJobInput) {
  const [job] = await db()<Pick<SearchJob, "id">[]>`
    insert into search_jobs (
      industry,
      location,
      target_record_count,
      selected_sources
    )
    values (
      ${input.industry},
      ${input.location},
      ${input.targetRecordCount},
      ${JSON.stringify(input.selectedSources)}::jsonb
    )
    returning id
  `;

  return job;
}

export async function getRecentJobs(limit = 8) {
  return db()<SearchJob[]>`
    select
      id,
      industry,
      location,
      target_record_count,
      selected_sources,
      status,
      records_found,
      leads_created,
      qualified_leads,
      api_requests_used,
      error_message,
      created_at,
      started_at,
      finished_at
    from search_jobs
    order by created_at desc
    limit ${limit}
  `;
}

export async function getJob(jobId: string) {
  const [job] = await db()<SearchJob[]>`
    select
      id,
      industry,
      location,
      target_record_count,
      selected_sources,
      status,
      records_found,
      leads_created,
      qualified_leads,
      api_requests_used,
      error_message,
      created_at,
      started_at,
      finished_at
    from search_jobs
    where id = ${jobId}
    limit 1
  `;

  return job ?? null;
}

export async function getLeadsForJob(jobId: string) {
  return db()<LeadRow[]>`
    select
      id,
      canonical_name,
      phone,
      website_status,
      city,
      state,
      category,
      sources_found,
      source_count,
      best_source_url,
      alive_score,
      no_website_score,
      opportunity_score,
      status
    from leads
    where search_job_id = ${jobId}
    order by opportunity_score desc nulls last, created_at desc
    limit 100
  `;
}
