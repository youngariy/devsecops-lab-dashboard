import io
import json
import zipfile

from app.services.artifact_summary import summarize_artifact_archives


def _zip_with_json(name: str, payload: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name, json.dumps(payload))
    return buffer.getvalue()


def test_summarize_trivy_json_and_sarif_tool():
    trivy_payload = {
        "Results": [
            {
                "Vulnerabilities": [
                    {"Severity": "CRITICAL"},
                    {"Severity": "HIGH"},
                    {"Severity": "MEDIUM"},
                ]
            }
        ]
    }
    semgrep_sarif = {
        "runs": [
            {
                "tool": {"driver": {"name": "Semgrep"}},
                "results": [
                    {"level": "error"},
                    {"level": "warning"},
                ],
            }
        ]
    }
    archives = [
        ("trivy-scan", _zip_with_json("trivy-report.json", trivy_payload)),
        ("semgrep-scan", _zip_with_json("semgrep.sarif", semgrep_sarif)),
    ]

    summary = summarize_artifact_archives(archives)

    assert summary["tools"]["trivy"]["critical"] == 1
    assert summary["tools"]["trivy"]["high"] == 1
    assert summary["tools"]["trivy"]["medium"] == 1
    assert summary["tools"]["semgrep"]["high"] == 1
    assert summary["tools"]["semgrep"]["medium"] == 1
