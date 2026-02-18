import Link from "next/link";
import { getDeploymentData } from "../../lib/api";

const statusTone: Record<string, string> = {
  success: "tone-success",
  failure: "tone-failure",
  cancelled: "tone-warn",
  unknown: "tone-muted"
};

function flagLabel(value: boolean | null) {
  if (value === null) return "unknown";
  return value ? "yes" : "no";
}

export default async function DeploymentPage() {
  const deployment = await getDeploymentData();
  const latest = deployment?.latest_cd_run;

  return (
    <main className="page">
      <section className="hero reveal">
        <p className="eyebrow">Deployment Trust Signals</p>
        <h1>Deployment Information</h1>
        <p className="subtitle">
          Track the latest CD run and supply-chain verification signals.
        </p>
      </section>

      <section className="cards">
        <article className="card reveal delay-1">
          <h2>Environment</h2>
          <p className="metric metric-sm">{deployment?.environment ?? "unknown"}</p>
        </article>
        <article className="card reveal delay-2">
          <h2>Latest CD Status</h2>
          <p className={`pill ${statusTone[latest?.conclusion ?? "unknown"]}`}>
            {latest?.conclusion ?? "unknown"}
          </p>
        </article>
        <article className="card reveal delay-3">
          <h2>Image Tag</h2>
          <p className="metric metric-sm">{deployment?.supply_chain?.image_tag || "-"}</p>
        </article>
        <article className="card reveal delay-4">
          <h2>HTTPS Check</h2>
          <p className="metric metric-sm">{flagLabel(deployment?.supply_chain?.https_ok ?? null)}</p>
        </article>
      </section>

      <section className="panel reveal delay-2">
        <header className="panel-header">
          <h3>Supply Chain Controls</h3>
          <Link href="/">Back to Dashboard</Link>
        </header>
        <ul className="signal-list">
          <li>
            <span>SBOM generated</span>
            <strong>{deployment?.supply_chain?.sbom_generated ? "yes" : "no"}</strong>
          </li>
          <li>
            <span>Cosign signed</span>
            <strong>{deployment?.supply_chain?.cosign_signed ? "yes" : "no"}</strong>
          </li>
          <li>
            <span>Cosign verified</span>
            <strong>{deployment?.supply_chain?.cosign_verified ? "yes" : "no"}</strong>
          </li>
          <li>
            <span>Image digest</span>
            <strong className="digest">{deployment?.supply_chain?.image_digest || "-"}</strong>
          </li>
        </ul>
      </section>

      <section className="panel reveal delay-3">
        <header className="panel-header">
          <h3>Latest CD Run</h3>
          <span>{deployment?.has_cd_data ? "available" : "not available"}</span>
        </header>
        {!latest && <p className="empty">No CD execution data collected yet.</p>}
        {latest && (
          <ul className="signal-list">
            <li>
              <span>Workflow</span>
              <strong>{latest.workflow_name}</strong>
            </li>
            <li>
              <span>Branch</span>
              <strong>{latest.branch || "-"}</strong>
            </li>
            <li>
              <span>Commit</span>
              <strong className="digest">{latest.commit_sha || "-"}</strong>
            </li>
            <li>
              <span>Duration</span>
              <strong>{latest.duration !== null ? `${latest.duration}s` : "-"}</strong>
            </li>
            <li>
              <span>Run link</span>
              <strong>
                {latest.html_url ? (
                  <Link href={latest.html_url} target="_blank">
                    View
                  </Link>
                ) : (
                  "-"
                )}
              </strong>
            </li>
          </ul>
        )}
      </section>
    </main>
  );
}
