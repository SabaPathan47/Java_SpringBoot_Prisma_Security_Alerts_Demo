# GlobalInsure Claims Processing Service

A production-shaped **insurance claims processing microservice** (Spring Boot
3 / Java 17) with a full GitHub Actions CI/CD pipeline that includes three
AI review agents, multi-tool security scanning, and a GHCR-based deploy flow.

This is deliberately **not** an e-commerce demo — it models a regulated
domain: customers hold policies, file claims against them, claims go through
an approve/reject lifecycle with an audit trail, and payments are tracked
separately.

## Architecture

```
Customer 1---* Policy 1---* Claim 1---1 Payment
```

- **Domain**: `Customer`, `Policy`, `Claim` (`ClaimStatus`: SUBMITTED →
  UNDER_REVIEW → APPROVED/REJECTED → PAID), `Payment`
- **Layers**: `controller` → `service` (+ `service.impl`) → `repository`
  (Spring Data JPA) → PostgreSQL, versioned with Flyway (`V1__init_schema.sql`)
- **Security**: stateless Spring Security, BCrypt, security headers, Actuator
  health endpoints public, everything else authenticated
- **API docs**: springdoc-openapi at `/swagger-ui.html`
- **Business rules enforced in `ClaimServiceImpl`**: no claims on inactive or
  expired policies, claimed amount can't exceed coverage, no re-approving an
  already-resolved claim — exactly the kind of rules a unit test suite should
  pin down.

## Running locally

```bash
docker compose up --build
```

This starts Postgres + the service on `http://localhost:8080`.

## Testing

```bash
mvn test                              # unit tests (Surefire), excludes *IT.java
mvn verify -DskipUnitTests            # integration tests (Failsafe, Testcontainers)
```

## CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

Triggers on **push** and **pull_request** against `main` and `feature`.

| Stage | What it does | Blocking? |
|---|---|---|
| `build` | `mvn clean compile`, build report | Yes (compile errors) |
| `unit-test` | `mvn test` + JaCoCo, then **Agent 1** reviews the results | Yes |
| `integration-test` | `mvn verify` with Testcontainers-backed Postgres | Yes |
| `code-quality` | Checkstyle static analysis | Informational |
| `security-scan` | OWASP Dependency-Check + Trivy (fs & image) + Prisma Cloud (`twistcli`), then **Agent 2** gates the result | **Yes — blocks deploy** |
| `build-and-push` | Builds the Docker image, pushes to **GHCR** | Yes |
| `deploy` | **Agent 3** re-verifies every upstream gate + drafts release notes, then deploys | **Yes — fail closed** |

Every stage uploads a markdown report as a workflow artifact, and on pull
requests the three agent reports are posted directly as PR comments so
reviewers see PASS/BLOCK without opening the Actions tab.

## The 3 AI Agents

Full specs live in each agent's own `.md` file. Important note: since you
have an **NVIDIA API key, not an Anthropic key**, these agents call
**NVIDIA NIM** (`https://integrate.api.nvidia.com/v1/chat/completions`,
model `nvidia/llama-3.1-nemotron-70b-instruct`) — Claude models are only
reachable via `api.anthropic.com`, AWS Bedrock, GCP Vertex, or Azure/Foundry,
not via NVIDIA's API. Each agent isolates the model call in one function, so
switching providers later is a small, contained change.

| Agent | Location | Stage | Job |
|---|---|---|---|
| Agent 1 — Unit Test Quality Analyzer | `agents/unit-test-agent/` | `unit-test` | Reviews Surefire + JaCoCo results |
| Agent 2 — Security Scan Gatekeeper | `agents/security-agent/` | `security-scan` | Consolidates OWASP/Trivy/Prisma Cloud findings |
| Agent 3 — Deployment Readiness & Release Notes | `agents/deployment-agent/` | `deploy` | Fail-closed final gate + AI release notes |

**Design principle used throughout:** the LLM never *is* the safety gate by
itself. Each agent computes its PASS/BLOCK or GO/NO-GO verdict with plain
deterministic Python logic first (severity counts, test failure counts,
missing files = fail closed), and only asks the model to write the
human-readable narrative. This means a bad or hallucinated model response
can never silently let a vulnerable or broken build through.

## Required GitHub Secrets

| Secret | Used by |
|---|---|
| `NVIDIA_API_KEY` | All 3 agents |
| `PRISMA_COMPUTE_URL`, `PRISMA_ACCESS_KEY`, `PRISMA_SECRET_KEY` | Prisma Cloud scan (optional — skipped gracefully if unset) |
| `DEPLOY_HOST`, `DEPLOY_SSH_KEY` | `deploy` job (template — point at your real target) |
| `GITHUB_TOKEN` | Auto-provided by Actions, used for GHCR push |

## Branching model

- `main` — protected, deploy-triggering branch
- `feature` — integration branch for in-progress work; opens PRs into `main`

Both push and pull_request events run the full pipeline; only a **push to
`main`** triggers the actual `deploy` job.
