import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .artifact_summary import summarize_artifact_archives


class GithubServiceError(Exception):
    pass


class GithubService:
    def __init__(self, api_base: str, owner: str, repo: str, token: str = ""):
        self.api_base = api_base.rstrip("/")
        self.owner = owner
        self.repo = repo
        self.token = token

    def _build_request(self, url: str, accept: str = "application/vnd.github+json") -> Request:
        headers = {
            "Accept": accept,
            "User-Agent": "devsecops-lab-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return Request(url, headers=headers, method="GET")

    def _request_json(self, path: str) -> dict[str, Any]:
        url = f"{self.api_base}{path}"
        req = self._build_request(url=url)
        try:
            with urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            raise GithubServiceError(f"Failed GitHub API request: {url}") from exc

    def _request_bytes(self, path: str, accept: str = "application/octet-stream") -> bytes:
        url = f"{self.api_base}{path}"
        req = self._build_request(url=url, accept=accept)
        try:
            with urlopen(req, timeout=20) as response:
                return response.read()
        except (HTTPError, URLError) as exc:
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

    def list_run_artifacts(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._request_json(
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts"
        )
        artifacts = payload.get("artifacts", [])
        if not isinstance(artifacts, list):
            return []
        return artifacts

    def download_artifact_zip(self, artifact_id: int) -> bytes:
        return self._request_bytes(
            f"/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}/zip"
        )

    def build_run_summary(self, run_id: int) -> dict[str, Any]:
        archives: list[tuple[str, bytes]] = []
        try:
            artifacts = self.list_run_artifacts(run_id=run_id)
        except GithubServiceError:
            return {}

        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            artifact_id = artifact.get("id")
            if not isinstance(artifact_id, int):
                continue
            is_expired = bool(artifact.get("expired", False))
            if is_expired:
                continue
            artifact_name = str(artifact.get("name", f"artifact-{artifact_id}"))
            try:
                archive_bytes = self.download_artifact_zip(artifact_id=artifact_id)
            except GithubServiceError:
                continue
            archives.append((artifact_name, archive_bytes))
        return summarize_artifact_archives(archives)
