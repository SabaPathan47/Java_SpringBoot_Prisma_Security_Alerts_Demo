#!/usr/bin/env python3
"""
Agent 2 — Security Scan Gatekeeper
Consolidates OWASP Dependency-Check, Trivy (fs + image), and Prisma Cloud
(twistcli) results into one deterministic PASS/BLOCK verdict for the
security-scan stage of the pipeline.

Exit code 0 -> PASS, deployment allowed to proceed
Exit code 1 -> BLOCK, deployment stage is skipped
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"

REPORT_PATH = "reports/security-agent-report.md"

OWASP_REPORT = "target/dependency-check-report/dependency-check-report.json"
TRIVY_FS_REPORT = "reports/trivy-fs-report.json"
TRIVY_IMAGE_REPORT = "reports/trivy-image-report.json"
PRISMA_REPORT = "reports/prisma-image-report.json"


def safe_load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def analyze_owasp(data):
    findings = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    if not data:
        return findings, []
    details = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulnerabilities", []) or []:
            sev = (vuln.get("severity") or "LOW").upper()
            if sev not in findings:
                sev = "LOW"
            findings[sev] += 1
            details.append(f"{dep.get('fileName', 'unknown')}: {vuln.get('name')} ({sev})")
    return findings, details


def analyze_trivy(data):
    findings = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    secrets_found = 0
    details = []
    if not data:
        return findings, secrets_found, details
    for result in data.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities", []) or []:
            sev = (vuln.get("Severity") or "LOW").upper()
            if sev not in findings:
                sev = "LOW"
            findings[sev] += 1
            details.append(f"{result.get('Target')}: {vuln.get('VulnerabilityID')} ({sev})")
        secrets_found += len(result.get("Secrets", []) or [])
    return findings, secrets_found, details


def analyze_prisma(data):
    if not data:
        return None, []
    # Simplified twistcli-style summary shape: {"results":[{"complianceScanPassed":true/false,
    # "vulnerabilities":[...], "complianceIssues":[...]}]}
    results = data.get("results", [])
    if not results:
        return None, []
    r = results[0]
    passed = r.get("vulnerabilityScanPassed", True) and r.get("complianceScanPassed", True)
    issues = [f"{v.get('id')} ({v.get('severity')})" for v in r.get("vulnerabilities", []) or []]
    return passed, issues


def call_model(prompt: str) -> str:
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return "(NVIDIA_API_KEY not set — skipping narrative summary; deterministic verdict below still applies.)"
    body = json.dumps({
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": (
                "You are a strict application security engineer reviewing scan "
                "results for a banking/insurance Spring Boot microservice before "
                "production deployment. Be concise and specific. Do not invent "
                "CVE IDs or numbers not provided to you."
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 600,
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
        return f"(Model call failed: {exc}. Deterministic verdict below is unaffected.)"


def main():
    os.makedirs("reports", exist_ok=True)

    owasp_data = safe_load(OWASP_REPORT)
    trivy_fs_data = safe_load(TRIVY_FS_REPORT)
    trivy_img_data = safe_load(TRIVY_IMAGE_REPORT)
    prisma_data = safe_load(PRISMA_REPORT)

    owasp_counts, owasp_details = analyze_owasp(owasp_data)
    fs_counts, fs_secrets, fs_details = analyze_trivy(trivy_fs_data)
    img_counts, img_secrets, img_details = analyze_trivy(trivy_img_data)
    prisma_passed, prisma_issues = analyze_prisma(prisma_data)

    total_critical = owasp_counts["CRITICAL"] + fs_counts["CRITICAL"] + img_counts["CRITICAL"]
    total_high = owasp_counts["HIGH"] + fs_counts["HIGH"] + img_counts["HIGH"]
    total_secrets = fs_secrets + img_secrets

    reasons_to_block = []
    if total_critical > 0:
        reasons_to_block.append(f"{total_critical} CRITICAL severity vulnerability finding(s) detected.")
    if total_high > 0:
        reasons_to_block.append(f"{total_high} HIGH severity vulnerability finding(s) detected.")
    if total_secrets > 0:
        reasons_to_block.append(f"{total_secrets} exposed secret(s)/credential(s) detected by Trivy.")
    if prisma_passed is False:
        reasons_to_block.append("Prisma Cloud compliance/vulnerability policy scan FAILED.")

    verdict = "BLOCK" if reasons_to_block else "PASS"

    prompt = (
        "Security scan summary for a banking/insurance claims microservice:\n"
        f"- OWASP Dependency-Check: {owasp_counts}\n"
        f"- Trivy filesystem scan: {fs_counts}, secrets found: {fs_secrets}\n"
        f"- Trivy container image scan: {img_counts}, secrets found: {img_secrets}\n"
        f"- Prisma Cloud policy scan passed: {prisma_passed}\n"
        f"- Deterministic verdict already computed: {verdict}\n\n"
        "Write a 5-8 sentence security review for a pull request comment aimed at "
        "engineers: summarize overall risk posture, call out the most urgent "
        "category to fix first, and note this is a regulated financial services "
        "workload so CRITICAL/HIGH findings and any secret exposure must block release."
    )
    narrative = call_model(prompt)

    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Security Scan Gatekeeper Agent Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Verdict:** `{verdict}`",
        "",
        "## Findings Summary",
        "| Scanner | Critical | High | Medium | Low |",
        "|---|---|---|---|---|",
        f"| OWASP Dependency-Check | {owasp_counts['CRITICAL']} | {owasp_counts['HIGH']} | {owasp_counts['MEDIUM']} | {owasp_counts['LOW']} |",
        f"| Trivy (filesystem) | {fs_counts['CRITICAL']} | {fs_counts['HIGH']} | {fs_counts['MEDIUM']} | {fs_counts['LOW']} |",
        f"| Trivy (container image) | {img_counts['CRITICAL']} | {img_counts['HIGH']} | {img_counts['MEDIUM']} | {img_counts['LOW']} |",
        "",
        f"- Secrets detected: {total_secrets}",
        f"- Prisma Cloud policy scan passed: {prisma_passed if prisma_passed is not None else 'N/A (not run)'}",
        "",
        "## Agent Narrative",
        narrative,
        "",
    ]
    if reasons_to_block:
        lines += ["## Blocking Reasons", *[f"- {r}" for r in reasons_to_block], ""]

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))

    if verdict == "BLOCK":
        print("::error::Security Gatekeeper Agent verdict = BLOCK. Deployment will not proceed.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
