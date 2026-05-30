import Link from "next/link";
import { createSearchJobAction } from "@/app/actions";
import { hasDatabaseConfig } from "@/lib/db";
import { getRecentJobs } from "@/lib/leadbot";

type HomePageProps = {
  searchParams: Promise<{
    error?: string;
  }>;
};

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const databaseReady = hasDatabaseConfig();
  const jobs = databaseReady ? await getRecentJobs() : [];

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <strong>LeadBot</strong>
          <span>Internal lead discovery</span>
        </div>
      </header>

      <main className="main">
        {!databaseReady ? (
          <div className="alert alert-warning">DATABASE_URL is not configured.</div>
        ) : null}
        {params.error ? <div className="alert alert-error">{errorMessage(params.error)}</div> : null}

        <div className="split">
          <section className="panel">
            <div className="panel-header">
              <div className="panel-title">New Search</div>
            </div>
            <div className="panel-body">
              <form action={createSearchJobAction} className="form-grid">
                <label className="field">
                  <span className="label">Industry</span>
                  <input
                    className="input"
                    name="industry"
                    placeholder="HVAC"
                    required
                    maxLength={120}
                  />
                </label>

                <label className="field">
                  <span className="label">Location</span>
                  <input
                    className="input"
                    name="location"
                    placeholder="Houston TX"
                    required
                    maxLength={160}
                  />
                </label>

                <label className="field">
                  <span className="label">Target Records</span>
                  <input
                    className="input"
                    name="target_record_count"
                    type="number"
                    min="1"
                    max="5000"
                    defaultValue="500"
                    required
                  />
                </label>

                <div className="field">
                  <span className="label">Sources</span>
                  <div className="source-grid">
                    <label className="check-tile">
                      <input name="selected_sources" type="checkbox" value="yelp" defaultChecked />
                      <span>Yelp</span>
                    </label>
                    <label className="check-tile">
                      <input
                        name="selected_sources"
                        type="checkbox"
                        value="thumbtack"
                        defaultChecked
                      />
                      <span>Thumbtack</span>
                    </label>
                  </div>
                </div>

                <div className="button-row">
                  <button className="button" disabled={!databaseReady} type="submit">
                    Create Job
                  </button>
                </div>
              </form>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div className="panel-title">Recent Jobs</div>
            </div>
            {jobs.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Search</th>
                      <th>Status</th>
                      <th>Records</th>
                      <th>Leads</th>
                      <th>Qualified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.id}>
                        <td>
                          <Link href={`/jobs/${job.id}`}>
                            <strong>{job.industry}</strong>
                            <div className="subtle">{job.location}</div>
                          </Link>
                        </td>
                        <td>
                          <span className={`status status-${job.status}`}>{job.status}</span>
                        </td>
                        <td>{job.records_found}</td>
                        <td>{job.leads_created}</td>
                        <td>{job.qualified_leads}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty">No jobs yet.</div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function errorMessage(error: string) {
  if (error === "missing-fields") {
    return "Industry and location are required.";
  }
  if (error === "invalid-target") {
    return "Target records must be between 1 and 5000.";
  }
  return "Could not create the search job.";
}
