import Link from "next/link";
import { getDashboardData } from "../lib/api";

const statusTone: Record<string, string> = {
  success: "tone-success",
  failure: "tone-failure",
  cancelled: "tone-warn",
  unknown: "tone-muted"
};

export default async function HomePage() {
  const { summary, runs } = await getDashboardData();

  return (
    <main className="page">
      <section className="hero reveal">
        <p className="eyebrow">DevSecOps Lab Dashboard</p>
        <h1>Pipeline + Security Signal Board</h1>
        <p className="subtitle">
          Track CI, Security, and CD status with recent failures in one view.
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
          <h3>Recent Pipeline Runs</h3>
          <span>{runs.length} items</span>
        </header>
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
      </section>

      <section className="panel reveal delay-3">
        <header className="panel-header">
          <h3>Security Tool Summary</h3>
        </header>
        <pre className="json">
          {JSON.stringify(summary?.security_summary?.tools ?? {}, null, 2)}
        </pre>
      </section>
    </main>
  );
}
