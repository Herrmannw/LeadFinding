import Link from "next/link";
import { notFound } from "next/navigation";
import { getJob, getLeadsForJob } from "@/lib/leadbot";

type JobPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function JobPage({ params }: JobPageProps) {
  const { id } = await params;
  const job = await getJob(id);

  if (!job) {
    notFound();
  }

  const leads = await getLeadsForJob(job.id);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <Link href="/">
            <strong>LeadBot</strong>
          </Link>
          <span>{job.industry}</span>
        </div>
        <Link className="button button-secondary" href="/">
          New Search
        </Link>
      </header>

      <main className="main">
        <section className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">
                {job.industry} · {job.location}
              </div>
              <div className="subtle">Goal {job.target_record_count}</div>
            </div>
            <span className={`status status-${job.status}`}>{job.status}</span>
          </div>
          {job.error_message ? (
            <div className="panel-body">
              <div className="alert alert-error">{job.error_message}</div>
            </div>
          ) : null}
        </section>

        <section className="metric-grid">
          <div className="metric">
            <div className="metric-label">Records</div>
            <div className="metric-value">{job.records_found}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Leads</div>
            <div className="metric-value">{job.leads_created}</div>
          </div>
          <div className="metric">
            <div className="metric-label">Qualified</div>
            <div className="metric-value">{job.qualified_leads}</div>
          </div>
          <div className="metric">
            <div className="metric-label">API Calls</div>
            <div className="metric-value">{job.api_requests_used}</div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">Ranked Leads</div>
            <Link className="button button-secondary" href={`/jobs/${job.id}`}>
              Refresh
            </Link>
          </div>
          {leads.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Business</th>
                    <th>Category</th>
                    <th>Location</th>
                    <th>Phone</th>
                    <th>Sources</th>
                    <th>Website</th>
                    <th>Alive</th>
                    <th>No Site</th>
                    <th>Opportunity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.map((lead) => (
                    <tr key={lead.id}>
                      <td>
                        {lead.best_source_url ? (
                          <a href={lead.best_source_url} rel="noreferrer" target="_blank">
                            <strong>{lead.canonical_name}</strong>
                          </a>
                        ) : (
                          <strong>{lead.canonical_name}</strong>
                        )}
                      </td>
                      <td>{lead.category ?? "—"}</td>
                      <td>{[lead.city, lead.state].filter(Boolean).join(", ") || "—"}</td>
                      <td>{lead.phone ?? "—"}</td>
                      <td>
                        <div className="source-list">
                          {lead.sources_found.map((source) => (
                            <span className="source-pill" key={source}>
                              {source}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>{lead.website_status.replaceAll("_", " ")}</td>
                      <td className="score">{lead.alive_score ?? "—"}</td>
                      <td className="score">{lead.no_website_score ?? "—"}</td>
                      <td className="score">{lead.opportunity_score ?? "—"}</td>
                      <td>
                        <span className={`status status-${lead.status}`}>{lead.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">No leads yet.</div>
          )}
        </section>
      </main>
    </div>
  );
}
