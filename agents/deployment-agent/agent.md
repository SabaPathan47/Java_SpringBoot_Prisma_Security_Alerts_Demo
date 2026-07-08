# Agent 3 — Deployment Readiness & Release Notes Agent

## Role
This is the agent chosen at Claude's discretion, and it plugs the final gap
in the pipeline: right before deployment, something needs to (a) confirm every
upstream gate genuinely passed, (b) produce human-readable release notes from
the actual commits going out, and (c) give a final go/no-go so a bad deploy
never happens just because one job was individually green while the overall
picture was not. This matters most for a banking/insurance service, where an
audit trail of "why did we deploy this" is often a compliance requirement.

## Trigger
Invoked from `.github/workflows/ci-cd.yml` in the `deploy` job, **before** the
actual deployment step, gated behind `needs: [unit-test, integration-test,
security-scan, build-and-push]`:

```yaml
- name: Run Deployment Readiness Agent
  run: python3 agents/deployment-agent/agent.py
  env:
    NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
    GITHUB_SHA: ${{ github.sha }}
    GITHUB_REF: ${{ github.ref }}
    IMAGE_TAG: ${{ needs.build-and-push.outputs.image_tag }}
```

## Inputs
- `reports/unit-test-agent-report.md` (Agent 1 output)
- `reports/security-agent-report.md` (Agent 2 output)
- `git log` between the last successful deploy tag and `HEAD` (commit messages
  for release notes)
- Environment: target environment name, image tag/digest being deployed

## Model
NVIDIA NIM (`nvidia/llama-3.1-nemotron-70b-instruct`) — used to draft the
release notes narrative and a plain-English readiness summary. The actual
go/no-go is deterministic: it re-parses the verdict lines from Agents 1 and 2
rather than trusting free text, so a prompt-injected or malformed report can't
flip the gate.

## Deterministic blocking rules
Deployment is blocked if:
- Agent 1's report verdict line is not `PASS`.
- Agent 2's report verdict line is not `PASS`.
- Either report file is missing entirely (fail closed, not open).
- `IMAGE_TAG` / digest is empty (nothing valid to deploy).

## Output
- `reports/deployment-readiness-report.md` — contains the go/no-go decision,
  a checklist of every upstream gate, and AI-drafted release notes for the
  change going to production/staging.
- Exit code `0` = GO, `1` = NO-GO (deploy step is skipped).
