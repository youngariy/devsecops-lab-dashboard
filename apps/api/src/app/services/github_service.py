import json
from io import BytesIO
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


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

    def _request_bytes(self, path: str) -> bytes:
        url = f"{self.api_base}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "devsecops-lab-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = Request(url, headers=headers, method="GET")
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

    def get_security_summary_for_run(self, run_id: int) -> dict[str, Any]:
        expected_name = f"security-summary-run-{run_id}"
        artifacts_payload = self._request_json(
            f"/repos/{self.owner}/{self.repo}/actions/runs/{run_id}/artifacts"
        )
        artifacts = artifacts_payload.get("artifacts", [])
        if not isinstance(artifacts, list):
            return {}

        artifact_id: int | None = None
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("expired"):
                continue
            if artifact.get("name") == expected_name:
                candidate = artifact.get("id")
                if isinstance(candidate, int):
                    artifact_id = candidate
                    break

        if artifact_id is None:
            return {}

        archive = self._request_bytes(
            f"/repos/{self.owner}/{self.repo}/actions/artifacts/{artifact_id}/zip"
        )
        try:
            with ZipFile(BytesIO(archive), "r") as zip_file:
                for member in zip_file.namelist():
                    if member.endswith("security-summary.json"):
                        with zip_file.open(member) as fd:
                            payload = json.loads(fd.read().decode("utf-8"))
                            if isinstance(payload, dict):
                                return payload
                            return {}
        except (BadZipFile, KeyError, json.JSONDecodeError) as exc:
            raise GithubServiceError(
                f"Failed to parse security summary artifact for run {run_id}"
            ) from exc
        return {}
