# Agent 1 — Unit Test Quality Analyzer

## Role
Acts as an automated QA reviewer for the **unit-test** stage of the CI/CD pipeline.
It runs after `mvn test` (Surefire) and JaCoCo produce their reports, reads the
results, and decides — in plain language and a machine-readable verdict — whether
the unit test evidence is strong enough to let the pipeline continue.

## Trigger
Invoked from `.github/workflows/ci-cd.yml` in the `unit-test` job, **after**
tests have run, via:

```yaml
- name: Run Unit Test Analyzer Agent
  run: python3 agents/unit-test-agent/agent.py
  env:
    NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
```

## Inputs
| Source | Path |
|---|---|
| Surefire XML reports | `target/surefire-reports/*.xml` |
| JaCoCo coverage XML | `target/site/jacoco/jacoco.xml` |

## Model
- Provider: NVIDIA NIM (`https://integrate.api.nvidia.com/v1/chat/completions`)
- Model: `nvidia/llama-3.1-nemotron-70b-instruct` (swap to `claude-sonnet-5` on
  `api.anthropic.com/v1/messages` with `ANTHROPIC_API_KEY` if/when available —
  the agent code isolates this in a single `call_model()` function)

## What it checks
1. Total tests run, failed, skipped, errored.
2. Line/branch coverage percentage from JaCoCo.
3. Flags suspicious patterns: zero-assertion tests, disabled (`@Disabled`) tests,
   coverage below the **60% line coverage** gate already enforced by the JaCoCo
   Maven plugin (`pom.xml`), and any test class with 0 tests contributing to a
   service/controller package.
4. Produces a short human-readable review plus a strict verdict.

## Output
- Writes `reports/unit-test-agent-report.md` (uploaded as a workflow artifact
  and posted as a PR comment by the workflow).
- Exit code:
  - `0` → verdict `PASS` — pipeline continues to `integration-test`.
  - `1` → verdict `BLOCK` — pipeline fails the job, deployment cannot proceed.

## Verdict rules (deterministic guardrail, not left to the LLM alone)
The agent applies hard rules first (any failed test, or coverage < 60%, is an
automatic `BLOCK`) and only asks the model to produce the *narrative summary*
and secondary code-quality observations. This avoids relying on an LLM as the
sole safety gate — the LLM explains and advises, the Python code enforces.
