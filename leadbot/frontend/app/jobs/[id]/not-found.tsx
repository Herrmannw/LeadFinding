import Link from "next/link";

export default function NotFound() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <Link href="/">
            <strong>LeadBot</strong>
          </Link>
        </div>
      </header>
      <main className="main">
        <section className="panel">
          <div className="panel-header">
            <div className="panel-title">Job Not Found</div>
          </div>
          <div className="panel-body">
            <Link className="button button-secondary" href="/">
              Back
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
