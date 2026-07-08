#!/usr/bin/env python3
"""
Agent 1 — Unit Test Quality Analyzer
Reads Surefire + JaCoCo output, applies deterministic pass/fail rules,
then asks an LLM (NVIDIA NIM by default) to summarize findings in a report.

Exit code 0  -> PASS, pipeline continues
Exit code 1  -> BLOCK, pipeline/job fails
"""
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"

# To use real Claude instead (requires an Anthropic key, not an NVIDIA key):
# ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
# ANTHROPIC_MODEL   = "claude-sonnet-5"

MIN_LINE_COVERAGE_PCT = 60.0
REPORT_PATH = "reports/unit-test-agent-report.md"

SUREFIRE_GLOB = "target/surefire-reports/*.xml"
JACOCO_XML = "target/site/jacoco/jacoco.xml"


def parse_surefire():
    total = failures = errors = skipped = 0
    suites = []
    for path in glob.glob(SUREFIRE_GLOB):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        t = int(root.attrib.get("tests", 0))
        f = int(root.attrib.get("failures", 0))
        e = int(root.attrib.get("errors", 0))
        s = int(root.attrib.get("skipped", 0))
        total += t
        failures += f
        errors += e
        skipped += s
        suites.append({"name": root.attrib.get("name", path), "tests": t, "failures": f, "errors": e})
    return {"total": total, "failures": failures, "errors": errors, "skipped": skipped, "suites": suites}


def parse_jacoco_coverage():
    if not os.path.exists(JACOCO_XML):
        return None
    try:
        root = ET.parse(JACOCO_XML).getroot()
    except ET.ParseError:
        return None
    for counter in root.findall("counter"):
        if counter.attrib.get("type") == "LINE":
            covered = int(counter.attrib["covered"])
            missed = int(counter.attrib["missed"])
            total = covered + missed
            return round((covered / total) * 100, 2) if total else 0.0
    return None


def call_model(prompt: str) -> str:
    """Calls NVIDIA NIM's OpenAI-compatible chat completion endpoint."""
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return "(NVIDIA_API_KEY not set — skipping narrative summary; deterministic verdict below still applies.)"

    import urllib.request

    body = json.dumps({
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": (
                "You are a strict senior QA engineer reviewing unit test results "
                "for a banking/insurance Spring Boot microservice. Be concise, "
                "factual, and specific. Do not invent numbers not given to you."
            )},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }).encode("utf-8")

    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # network/model errors must not crash the gate
        return f"(Model call failed: {exc}. Deterministic verdict below is unaffected.)"


def main():
    os.makedirs("reports", exist_ok=True)

    surefire = parse_surefire()
    coverage = parse_jacoco_coverage()

    reasons_to_block = []
    if surefire["total"] == 0:
        reasons_to_block.append("No unit tests were detected — Surefire reported zero tests.")
    if surefire["failures"] > 0:
        reasons_to_block.append(f"{surefire['failures']} unit test(s) failed.")
    if surefire["errors"] > 0:
        reasons_to_block.append(f"{surefire['errors']} unit test(s) errored.")
    if coverage is None:
        reasons_to_block.append("JaCoCo coverage report not found.")
    elif coverage < MIN_LINE_COVERAGE_PCT:
        reasons_to_block.append(
            f"Line coverage {coverage}% is below the required {MIN_LINE_COVERAGE_PCT}% threshold."
        )

    verdict = "BLOCK" if reasons_to_block else "PASS"

    prompt = (
        f"Unit test run summary:\n"
        f"- Total tests: {surefire['total']}\n"
        f"- Failures: {surefire['failures']}\n"
        f"- Errors: {surefire['errors']}\n"
        f"- Skipped: {surefire['skipped']}\n"
        f"- Line coverage: {coverage if coverage is not None else 'unknown'}%\n"
        f"- Deterministic verdict already computed: {verdict}\n\n"
        f"Write a 4-6 sentence review for a pull request comment: mention notable "
        f"risk areas, whether coverage is healthy for a financial services claims "
        f"microservice, and one concrete improvement suggestion."
    )
    narrative = call_model(prompt)

    timestamp = datetime.now(timezone.utc).isoformat()
    report_lines = [
        "# Unit Test Analyzer Agent Report",
        "",
        f"**Generated:** {timestamp}",
        f"**Verdict:** `{verdict}`",
        "",
        "## Metrics",
        f"- Total tests: {surefire['total']}",
        f"- Failures: {surefire['failures']}",
        f"- Errors: {surefire['errors']}",
        f"- Skipped: {surefire['skipped']}",
        f"- Line coverage: {coverage if coverage is not None else 'N/A'}%"
        f" (gate: {MIN_LINE_COVERAGE_PCT}%)",
        "",
        "## Agent Narrative",
        narrative,
        "",
    ]
    if reasons_to_block:
        report_lines += ["## Blocking Reasons", *[f"- {r}" for r in reasons_to_block], ""]

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(report_lines))

    print("\n".join(report_lines))

    if verdict == "BLOCK":
        print("::error::Unit Test Analyzer Agent verdict = BLOCK. Failing pipeline.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
