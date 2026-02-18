import Link from "next/link";
import { getDashboardData } from "../lib/api";

const statusTone: Record<string, string> = {
  success: "tone-success",
  failure: "tone-failure",
  cancelled: "tone-warn",
  unknown: "tone-muted"
};

type HomeProps = {
  searchParams?: {
    page?: string;
    category?: string;
    branch?: string;
  };
};

export default async function HomePage({ searchParams }: HomeProps) {
  const pageValue = Number(searchParams?.page ?? "1");
  const selectedCategory = (searchParams?.category ?? "").trim().toLowerCase();
  const selectedBranch = (searchParams?.branch ?? "").trim();
  const currentPage = Number.isFinite(pageValue) && pageValue > 0 ? Math.floor(pageValue) : 1;
  const { summary, runs, totalPages, totalRuns, trends } = await getDashboardData(
    currentPage,
    10,
    selectedCategory,
    selectedBranch
  );
  const pageNumbers = Array.from({ length: totalPages }, (_, idx) => idx + 1);
  const securitySummary = summary?.security_summary;
  const severityOrder = ["critical", "high", "medium", "low", "unknown"];
  const toolOrder = ["trivy", "bandit", "semgrep", "pip_audit", "gitleaks", "zap"];
  const trendMax = Math.max(1, ...trends.map((point) => point.total_findings));
  const buildPageHref = (page: number) => {
    const params = new URLSearchParams({ page: String(page) });
    if (selectedCategory) params.set("category", selectedCategory);
    if (selectedBranch) params.set("branch", selectedBranch);
    return `/?${params.toString()}`;
  };

  return (
    <main className="page">
      <section className="hero reveal">
        <p className="eyebrow">DevSecOps Lab Dashboard</p>
        <h1>Pipeline + Security Signal Board</h1>
        <p className="subtitle">
          Track CI, Security, and CD status with recent failures in one view.
        </p>
        <p className="hero-link">
          <Link href="/deployment">Go to Deployment Info</Link>
        </p>
      </section>

      <section className="cards">
        <article className="card reveal delay-1">
          <h2>Total Runs</h2>
          <p className="metric">{summary?.total_runs ?? 0}</p>
        </article>
        <article className="card reveal delay-2">
          <h2>CI</h2>
          <p className={`pill ${statusTone[summary?.category_status?.ci ?? "unknown"]}`}>
            {summary?.category_status?.ci ?? "unknown"}
          </p>
        </article>
        <article className="card reveal delay-3">
          <h2>Security</h2>
          <p className={`pill ${statusTone[summary?.category_status?.security ?? "unknown"]}`}>
            {summary?.category_status?.security ?? "unknown"}
          </p>
        </article>
        <article className="card reveal delay-4">
          <h2>CD</h2>
          <p className={`pill ${statusTone[summary?.category_status?.cd ?? "unknown"]}`}>
            {summary?.category_status?.cd ?? "unknown"}
          </p>
        </article>
      </section>

      <section className="panel reveal delay-2">
        <header className="panel-header">
          <h3>Security Findings Summary</h3>
          <span>
            Secret leak: {securitySummary?.secret_leak_detected ? "detected" : "not detected"}
          </span>
        </header>
        <div className="security-grid">
          <article className="security-block">
            <h4>Severity Totals</h4>
            <div className="severity-list">
              {severityOrder.map((severity) => (
                <span key={severity} className={`severity-chip severity-${severity}`}>
                  {severity}: {securitySummary?.severity_totals?.[severity] ?? 0}
                </span>
              ))}
            </div>
          </article>
          <article className="security-block">
            <h4>Tool Totals</h4>
            <ul className="tool-list">
              {toolOrder.map((tool) => (
                <li key={tool}>
                  <span>{tool}</span>
                  <strong>{securitySummary?.tool_totals?.[tool] ?? 0}</strong>
                </li>
              ))}
            </ul>
          </article>
          <article className="security-block">
            <h4>Supply Chain Signals</h4>
            <ul className="signal-list">
              <li>
                <span>SBOM generated</span>
                <strong>{securitySummary?.supply_chain?.sbom_generated ? "yes" : "no"}</strong>
              </li>
              <li>
                <span>Cosign signed</span>
                <strong>{securitySummary?.supply_chain?.cosign_signed ? "yes" : "no"}</strong>
              </li>
              <li>
                <span>Cosign verified</span>
                <strong>{securitySummary?.supply_chain?.cosign_verified ? "yes" : "no"}</strong>
              </li>
            </ul>
          </article>
        </div>
      </section>

      <section className="panel reveal delay-3">
        <header className="panel-header">
          <h3>Security Findings Trend (14d)</h3>
          <span>{trends.reduce((sum, point) => sum + point.total_findings, 0)} findings</span>
        </header>
        {trends.length === 0 && <p className="empty">No trend data collected yet.</p>}
        {trends.length > 0 && (
          <div className="trend-chart" style={{ gridTemplateColumns: `repeat(${trends.length}, minmax(0, 1fr))` }}>
            {trends.map((point) => {
              const height = Math.max(6, Math.round((point.total_findings / trendMax) * 100));
              return (
                <div key={point.date} className="trend-bar-wrap">
                  <span className="trend-value">{point.total_findings}</span>
                  <div className="trend-bar" style={{ height: `${height}%` }} />
                  <span className="trend-label">{point.date.slice(5)}</span>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel reveal delay-2">
        <header className="panel-header">
          <h3>Recent Pipeline Runs</h3>
          <span>{totalRuns} total</span>
        </header>
        <form className="filters" method="get">
          <label>
            Category
            <select name="category" defaultValue={selectedCategory}>
              <option value="">all</option>
              <option value="ci">ci</option>
              <option value="security">security</option>
              <option value="cd">cd</option>
              <option value="other">other</option>
            </select>
          </label>
          <label>
            Branch
            <input name="branch" placeholder="main" defaultValue={selectedBranch} />
          </label>
          <button type="submit">Apply</button>
          <Link href="/">Reset</Link>
        </form>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Status</th>
                <th>Branch</th>
                <th>Duration</th>
                <th>Run</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty">
                    No runs collected yet, or the backend API is not reachable.
                  </td>
                </tr>
              )}
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.workflow_name}</td>
                  <td>
                    <span className={`pill ${statusTone[run.conclusion] ?? statusTone.unknown}`}>
                      {run.conclusion}
                    </span>
                  </td>
                  <td>{run.branch || "-"}</td>
                  <td>{run.duration !== null ? `${run.duration}s` : "-"}</td>
                  <td>
                    {run.html_url ? (
                      <Link href={run.html_url} target="_blank">
                        View
                      </Link>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {totalPages > 1 && (
          <nav className="pagination" aria-label="Pipeline runs pages">
            <Link href={buildPageHref(Math.max(1, currentPage - 1))} aria-disabled={currentPage === 1}>
              Prev
            </Link>
            {pageNumbers.map((page) => (
              <Link key={page} href={buildPageHref(page)} aria-current={page === currentPage ? "page" : undefined}>
                {page}
              </Link>
            ))}
            <Link
              href={buildPageHref(Math.min(totalPages, currentPage + 1))}
              aria-disabled={currentPage === totalPages}
            >
              Next
            </Link>
          </nav>
        )}
      </section>
    </main>
  );
}
