export type PipelineRun = {
  id: number;
  workflow_name: string;
  category: string;
  conclusion: string;
  branch: string;
  commit_sha: string;
  started_at: string;
  completed_at: string;
  duration: number | null;
  html_url: string;
};

export type DeploymentSummary = {
  has_cd_data: boolean;
  latest_cd_run: {
    id: number;
    workflow_name: string;
    conclusion: string;
    branch: string;
    commit_sha: string;
    duration: number | null;
    started_at: string;
    completed_at: string;
    html_url: string;
  } | null;
  environment: string;
  supply_chain: {
    sbom_generated: boolean;
    cosign_signed: boolean;
    cosign_verified: boolean;
    https_ok: boolean | null;
    image_digest: string;
    image_tag: string;
  };
};

export type SecurityTrendPoint = {
  date: string;
  total_findings: number;
  severity_totals: Record<string, number>;
};

export type SecurityTrendResponse = {
  days: number;
  points: SecurityTrendPoint[];
};

type RunsResponse = {
  count: number;
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  filters?: {
    category?: string;
    branch?: string;
  };
  items: PipelineRun[];
};

type SummaryResponse = {
  total_runs: number;
  status_counts: Record<string, number>;
  category_status: Record<string, string>;
  recent_failures: PipelineRun[];
  security_summary: {
    severity_totals: Record<string, number>;
    tool_totals: Record<string, number>;
    tool_severity: Record<string, Record<string, number>>;
    secret_leak_detected: boolean;
    supply_chain: {
      sbom_generated: boolean;
      cosign_signed: boolean;
      cosign_verified: boolean;
    };
  };
};

function apiBase(): string {
  const explicitBase =
    process.env.API_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? "http://api:5000";
  return explicitBase.replace(/\/$/, "");
}

async function safeFetch<T>(path: string): Promise<T | null> {
  try {
    const base = apiBase();
    const res = await fetch(`${base}${path}`, { cache: "no-store" });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getDashboardData(page = 1, limit = 10, category = "", branch = "") {
  const safePage = Math.max(1, page);
  const safeLimit = Math.max(1, Math.min(limit, 100));
  const params = new URLSearchParams({
    limit: String(safeLimit),
    page: String(safePage)
  });
  if (category.trim()) {
    params.set("category", category.trim().toLowerCase());
  }
  if (branch.trim()) {
    params.set("branch", branch.trim());
  }
  const [summary, runs, trends] = await Promise.all([
    safeFetch<SummaryResponse>("/api/pipelines/summary"),
    safeFetch<RunsResponse>(`/api/pipelines/runs?${params.toString()}`),
    safeFetch<SecurityTrendResponse>("/api/pipelines/security-trends?days=14")
  ]);
  return {
    summary,
    runs: runs?.items ?? [],
    runsPage: runs?.page ?? safePage,
    totalPages: runs?.total_pages ?? 1,
    totalRuns: runs?.total ?? 0,
    activeFilters: runs?.filters ?? {},
    trends: trends?.points ?? []
  };
}

export async function getDeploymentData() {
  return safeFetch<DeploymentSummary>("/api/pipelines/deployment");
}
