import io
import json
import zipfile
from collections import defaultdict
from typing import Any


SEVERITY_KEYS = ("critical", "high", "medium", "low", "unknown")


def _normalize_tool_name(name: str) -> str:
    lowered = name.lower()
    if "pip-audit" in lowered or "pip_audit" in lowered or "pipaudit" in lowered:
        return "pip_audit"
    if "semgrep" in lowered:
        return "semgrep"
    if "bandit" in lowered:
        return "bandit"
    if "trivy" in lowered:
        return "trivy"
    if "gitleaks" in lowered:
        return "gitleaks"
    return ""


def _normalize_severity(value: str) -> str:
    lowered = (value or "").strip().lower()
    if lowered in {"critical", "high", "medium", "low"}:
        return lowered
    if lowered in {"error"}:
        return "high"
    if lowered in {"warning", "warn"}:
        return "medium"
    if lowered in {"note", "info", "information"}:
        return "low"
    return "unknown"


def _empty_tool_counts() -> dict[str, int]:
    return {severity: 0 for severity in SEVERITY_KEYS}


def _detect_sbom_signal(file_name: str, payload: Any) -> bool:
    lowered = file_name.lower()
    if "sbom" in lowered or "cyclonedx" in lowered or "spdx" in lowered:
        return True
    if isinstance(payload, dict) and "bomFormat" in payload:
        return True
    return False


def _iter_pairs(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield str(key), value
            yield from _iter_pairs(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_pairs(item)


def _looks_like_digest(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("sha256:") and len(lowered) > len("sha256:")


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "pass", "passed", "ok", "healthy", "success"}:
            return True
        if lowered in {"false", "no", "fail", "failed", "error", "unhealthy"}:
            return False
    return None


def _extract_supply_chain_signals(payload: Any) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    for key, value in _iter_pairs(payload):
        lowered_key = key.lower()
        bool_value = _as_bool(value)

        if lowered_key in {"sbom_generated", "sbom", "sbom_created"} and bool_value is not None:
            signals["sbom_generated"] = bool_value
        if lowered_key in {"cosign_signed", "signed"} and bool_value is not None:
            signals["cosign_signed"] = bool_value
        if lowered_key in {"cosign_verified", "verified", "signature_verified"} and bool_value is not None:
            signals["cosign_verified"] = bool_value
        if "https" in lowered_key and bool_value is not None:
            signals["https_ok"] = bool_value

        if lowered_key in {"image_digest", "digest", "container_digest"} and isinstance(value, str):
            if _looks_like_digest(value):
                signals["image_digest"] = value
        if lowered_key in {"image_tag", "tag", "release_tag"} and isinstance(value, str) and value.strip():
            signals["image_tag"] = value.strip()
    return signals


def _collect_json_findings(payload: Any) -> list[str]:
    findings: list[str] = []
    if isinstance(payload, dict):
        for key in ("severity", "level", "issue_severity", "Severity"):
            if key in payload and isinstance(payload[key], str):
                findings.append(payload[key])
        for key in ("results", "vulnerabilities", "findings"):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    findings.extend(_collect_json_findings(item))
        if "Results" in payload and isinstance(payload["Results"], list):
            for result in payload["Results"]:
                if isinstance(result, dict):
                    vulns = result.get("Vulnerabilities", [])
                    if isinstance(vulns, list):
                        for vuln in vulns:
                            findings.extend(_collect_json_findings(vuln))
        if "dependencies" in payload and isinstance(payload["dependencies"], list):
            for dep in payload["dependencies"]:
                if isinstance(dep, dict):
                    for vuln in dep.get("vulns", []):
                        findings.extend(_collect_json_findings(vuln))
                    for vuln in dep.get("vulnerabilities", []):
                        findings.extend(_collect_json_findings(vuln))
    elif isinstance(payload, list):
        for item in payload:
            findings.extend(_collect_json_findings(item))
    return findings


def _tool_from_payload_or_name(payload: Any, artifact_name: str, file_name: str) -> str:
    if isinstance(payload, dict):
        sarif_runs = payload.get("runs", [])
        if isinstance(sarif_runs, list) and sarif_runs:
            first_run = sarif_runs[0]
            if isinstance(first_run, dict):
                tool_name = (
                    first_run.get("tool", {})
                    .get("driver", {})
                    .get("name", "")
                )
                normalized = _normalize_tool_name(str(tool_name))
                if normalized:
                    return normalized
    for candidate in (file_name, artifact_name):
        normalized = _normalize_tool_name(candidate)
        if normalized:
            return normalized
    return ""


def _extract_sarif_levels(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        return findings
    for run in runs:
        if not isinstance(run, dict):
            continue
        results = run.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if isinstance(result, dict):
                level = result.get("level")
                if isinstance(level, str):
                    findings.append(level)
    return findings


def summarize_artifact_archives(artifact_archives: list[tuple[str, bytes]]) -> dict[str, Any]:
    tool_counts: dict[str, dict[str, int]] = defaultdict(_empty_tool_counts)
    supply_chain = {
        "sbom_generated": False,
        "cosign_signed": False,
        "cosign_verified": False,
        "https_ok": None,
        "image_digest": "",
        "image_tag": "",
    }

    for artifact_name, archive_bytes in artifact_archives:
        try:
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
                members = zf.namelist()
                for member in members:
                    lowered_name = member.lower()
                    if lowered_name.endswith("/") or not lowered_name.endswith((".json", ".sarif")):
                        if "cosign" in lowered_name and "sign" in lowered_name:
                            supply_chain["cosign_signed"] = True
                        if "cosign" in lowered_name and "verif" in lowered_name:
                            supply_chain["cosign_verified"] = True
                        continue
                    with zf.open(member) as handle:
                        raw_bytes = handle.read()
                    try:
                        payload = json.loads(raw_bytes.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue

                    if _detect_sbom_signal(member, payload):
                        supply_chain["sbom_generated"] = True
                    extracted_signals = _extract_supply_chain_signals(payload)
                    for key, value in extracted_signals.items():
                        if key in {"sbom_generated", "cosign_signed", "cosign_verified"} and bool(value):
                            supply_chain[key] = True
                        elif key == "https_ok":
                            supply_chain[key] = value
                        elif key in {"image_digest", "image_tag"} and isinstance(value, str) and value:
                            supply_chain[key] = value

                    tool = _tool_from_payload_or_name(payload, artifact_name, member)
                    if not tool:
                        continue

                    findings = (
                        _extract_sarif_levels(payload)
                        if lowered_name.endswith(".sarif")
                        else _collect_json_findings(payload)
                    )
                    for finding in findings:
                        sev = _normalize_severity(finding)
                        tool_counts[tool][sev] += 1
        except zipfile.BadZipFile:
            continue

    summary: dict[str, Any] = {}
    if tool_counts:
        summary["tools"] = dict(tool_counts)
    if (
        supply_chain["sbom_generated"]
        or supply_chain["cosign_signed"]
        or supply_chain["cosign_verified"]
        or supply_chain["https_ok"] is not None
        or bool(supply_chain["image_digest"])
        or bool(supply_chain["image_tag"])
    ):
        summary["supply_chain"] = supply_chain
    return summary
