import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class GithubServiceError(Exception):
    pass


class GithubService:
    def __init__(self, api_base: str, owner: str, repo: str, token: str = ""):
        self.api_base = api_base.rstrip("/")
        self.owner = owner
        self.repo = repo
        self.token = token

    def _request_json(self, path: str) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "devsecops-lab-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(url, headers=headers, method="GET")
        try:
            with urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            raise GithubServiceError(f"Failed GitHub API request: {url}") from exc

    def list_workflow_runs(self, per_page: int = 30) -> list[dict[str, Any]]:
        path = (
            f"/repos/{self.owner}/{self.repo}/actions/runs"
            f"?per_page={per_page}"
        )
        payload = self._request_json(path)
        runs = payload.get("workflow_runs", [])
        if not isinstance(runs, list):
            return []
        return runs
