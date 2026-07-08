# Agent 2 — Security Scan Gatekeeper

## Role
Acts as the automated security reviewer for the **security-scan** stage. It
consolidates output from multiple scanners — OWASP Dependency-Check, Trivy
(filesystem + container image), and Prisma Cloud (`twistcli`) image scan —
into a single risk verdict that can **block deployment** for a banking/
insurance workload.

## Trigger
Invoked from `.github/workflows/ci-cd.yml` in the `security-scan` job:

```yaml
- name: Run Security Gatekeeper Agent
  run: python3 agents/security-agent/agent.py
  env:
    NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
```

## Inputs
| Scanner | Report path | Purpose |
|---|---|---|
| OWASP Dependency-Check | `target/dependency-check-report/dependency-check-report.json` | Known CVEs in Maven dependencies |
| Trivy (filesystem) | `reports/trivy-fs-report.json` | OS/library vulnerabilities, secrets, misconfig in repo |
| Trivy (image) | `reports/trivy-image-report.json` | Vulnerabilities baked into the built container image |
| Prisma Cloud (`twistcli`) | `reports/prisma-image-report.json` | Enterprise image compliance + vulnerability policy scan |

## Model
NVIDIA NIM (`nvidia/llama-3.1-nemotron-70b-instruct`), same pattern as Agent 1.
The LLM is used only to **explain and prioritize** findings for humans; the
actual pass/fail gate is computed deterministically from severity counts so a
model hallucination can never silently let a critical CVE through.

## Deterministic blocking rules
The pipeline is **blocked** (deployment stopped) if any of the following is true:
- Any dependency/image finding at **CRITICAL** severity.
- More than **0** HIGH severity findings with a known fix available and no
  suppression entry in `security/owasp-suppressions.xml`.
- Prisma Cloud reports a policy result of `fail` (compliance or vulnerability
  policy violation).
- Any exposed secret/credential is detected by Trivy's secret scanner.

Anything else (MEDIUM/LOW, or HIGH without an available fix) is reported but
does not block — it's logged as a tracked follow-up in the report.

## Output
- `reports/security-agent-report.md` — human-readable pass/fail report with a
  findings table, uploaded as a workflow artifact and posted as a PR comment.
- Exit code `0` = PASS (deploy allowed to proceed), `1` = BLOCK (deploy job is
  skipped via `needs` + job status check in the workflow).
