#!/usr/bin/env python3
"""
Agent 3 — Deployment Readiness & Release Notes Agent
Re-checks upstream agent verdicts deterministically (fail-closed), drafts
release notes from git log, and issues a final GO / NO-GO before deployment.

Exit code 0 -> GO, deploy proceeds
Exit code 1 -> NO-GO, deploy step is skipped
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"

REPORT_PATH = "reports/deployment-readiness-report.md"
UNIT_TEST_REPORT = "reports/unit-test-agent-report.md"
SECURITY_REPORT = "reports/security-agent-report.md"


def extract_verdict(path):
    """Fail-closed: missing file or missing verdict line == BLOCK."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for line in f:
            if line.strip().startswith("**Verdict:**"):
                if "PASS" in line:
                    return "PASS"
                if "BLOCK" in line:
                    return "BLOCK"
    return None


def get_recent_commits(max_count=15):
    try:
        out = subprocess.run(
            ["git", "log", f"-{max_count}", "--pretty=format:%h %s (%an)"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return out.stdout.strip().splitlines() if out.returncode == 0 else []
    except Exception:
        return []


def call_model(prompt: str) -> str:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return "(NVIDIA_API_KEY not set — skipping AI-drafted release notes.)"
    body = json.dumps({
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": (
                "You write concise, professional release notes for a regulated "
                "banking/insurance microservice deployment. Group changes into "
                "Features, Fixes, and Other. Do not invent commits not given to you."
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }).encode("utf-8")
    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"(Model call failed: {exc}. GO/NO-GO decision below is unaffected.)"


def main():
    os.makedirs("reports", exist_ok=True)

    unit_verdict = extract_verdict(UNIT_TEST_REPORT)
    security_verdict = extract_verdict(SECURITY_REPORT)
    image_tag = os.environ.get("IMAGE_TAG", "").strip()
    sha = os.environ.get("GITHUB_SHA", "unknown")[:8]
    ref = os.environ.get("GITHUB_REF", "unknown")

    checklist = [
        ("Unit Test Analyzer Agent verdict == PASS", unit_verdict == "PASS"),
        ("Security Gatekeeper Agent verdict == PASS", security_verdict == "PASS"),
        ("Container image tag/digest present", bool(image_tag)),
    ]
    reasons_to_block = [name for name, ok in checklist if not ok]
    decision = "NO-GO" if reasons_to_block else "GO"

    commits = get_recent_commits()
    commit_block = "\n".join(commits) if commits else "(no git history available in this context)"
    prompt = (
        f"Draft release notes for deployment of commit {sha} on ref {ref}, "
        f"image tag {image_tag or 'UNKNOWN'}, to the target environment.\n\n"
        f"Recent commits:\n{commit_block}\n\n"
        f"Also state in one sentence whether this looks like a routine change "
        f"or something that warrants extra manual review before a production "
        f"banking/insurance deployment."
    )
    release_notes = call_model(prompt)

    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Deployment Readiness & Release Notes Agent Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Decision:** `{decision}`",
        f"**Commit:** `{sha}`  **Ref:** `{ref}`  **Image tag:** `{image_tag or 'N/A'}`",
        "",
        "## Readiness Checklist",
        *[f"- [{'x' if ok else ' '}] {name}" for name, ok in checklist],
        "",
        "## AI-Drafted Release Notes",
        release_notes,
        "",
    ]
    if reasons_to_block:
        lines += ["## Blocking Reasons", *[f"- {r}" for r in reasons_to_block], ""]

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))

    if decision == "NO-GO":
        print("::error::Deployment Readiness Agent decision = NO-GO. Deployment will not proceed.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
