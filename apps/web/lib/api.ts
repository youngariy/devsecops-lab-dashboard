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

type RunsResponse = {
  count: number;
  total: number;
  page: number;
  limit: number;
  total_pages: number;
  items: PipelineRun[];
};

type SummaryResponse = {
  total_runs: number;
  status_counts: Record<string, number>;
  category_status: Record<string, string>;
  recent_failures: PipelineRun[];
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

export async function getDashboardData(page = 1, limit = 10) {
  const safePage = Math.max(1, page);
  const safeLimit = Math.max(1, Math.min(limit, 100));
  const [summary, runs] = await Promise.all([
    safeFetch<SummaryResponse>("/api/pipelines/summary"),
    safeFetch<RunsResponse>(`/api/pipelines/runs?limit=${safeLimit}&page=${safePage}`)
  ]);
  return {
    summary,
    runs: runs?.items ?? [],
    runsPage: runs?.page ?? safePage,
    totalPages: runs?.total_pages ?? 1,
    totalRuns: runs?.total ?? 0
  };
}
