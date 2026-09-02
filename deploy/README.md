# RegOntology delivery guide

This directory contains the local Docker Compose profile and the container build/release configuration for the executable MVP. Local and CI runs use only `mock-data/` and the deterministic `fake` AI provider by default; an OpenAI API key is optional and can be added later.

## Local prerequisites

- Docker Desktop with Docker Compose v2
- PowerShell 7 (`pwsh`) for the helper script
- At least 4 GB of memory available to Docker
- Free loopback ports `8080`, `8000`, `5432`, `7474`, `7687`, and `6379`

`scripts/dev.ps1` first uses `docker` from `PATH`. If the current PowerShell
session has not picked up Docker Desktop's PATH update yet, it also discovers
the standard per-user and all-users Docker Desktop CLI locations automatically.
Docker Desktop itself must still be running with the Linux container engine.

The data-service ports are bound to `127.0.0.1`, not to every host interface. The local data bridge is routable so Docker Desktop can publish those loopback-only diagnostic ports; it is not the production network design. The application containers run without Linux capabilities and with read-only root filesystems. PostgreSQL and Neo4j keep their local state in named Docker volumes.

## Start the complete stack

From the repository root on Windows:

```powershell
pwsh ./scripts/dev.ps1 bootstrap
```

The command creates a git-ignored `.env.local` with random, URL-safe PostgreSQL, Neo4j, and Redis passwords, validates the Compose model, builds both application images, starts all services, and waits for their health checks.

The API container runs the canonical bootstrap in order: `alembic -c alembic.ini upgrade head`, deterministic mock seed into PostgreSQL/pgvector, Neo4j projection rebuild, then FastAPI. Re-running bootstrap is idempotent; PostgreSQL remains the source of truth and Neo4j can be rebuilt from the active publication.

It intentionally does not modify the pre-existing root `.env`, because that file can belong to another local project. Every direct Compose command must therefore specify the project environment file:

```powershell
docker compose --env-file .env.local ps
docker compose --env-file .env.local logs --tail 200
docker compose --env-file .env.local down --remove-orphans
```

Test endpoints after bootstrap:

- Web application: <http://127.0.0.1:8080>
- API health: <http://127.0.0.1:8000/api/v1/health>
- API documentation: <http://127.0.0.1:8000/api/docs>
- Neo4j Browser (local diagnostics): <http://127.0.0.1:7474>

Stopping the stack does not delete PostgreSQL or Neo4j volumes. Volume deletion is deliberately not included in the helper script because it destroys local data.

## Day-to-day commands

```powershell
pwsh ./scripts/dev.ps1 up
pwsh ./scripts/dev.ps1 status
pwsh ./scripts/dev.ps1 health
pwsh ./scripts/dev.ps1 logs -Follow
pwsh ./scripts/dev.ps1 test
pwsh ./scripts/dev.ps1 down
```

GNU Make wrappers are also available, for example `make bootstrap`, `make test`, and `make down`.

The test command builds the Dockerfiles' `test` stages. Backend lint, strict type checking, and pytest execute inside the backend test image. Frontend type checking, Vitest, and its production build execute inside the frontend test image.

The frontend build also produces and verifies `dist/server/index.js`, the optional edge-hosting worker. The nginx runtime image deliberately packages only the static SPA assets because nginx provides the SPA fallback and `/api/` reverse proxy in the Docker profile. A Celery application/entry point is not part of this MVP, so Compose does not start a misleading asynchronous worker container; Redis is provisioned for that planned phase. Add a separately tested worker image and service when ingestion/indexing jobs are implemented.

### Demo fallback boundary

The Dockerfile defaults `VITE_DEMO_MODE=false`, and both Compose and the GHCR workflow pass that build argument explicitly. Consequently, a containerized frontend displays API 5xx, timeout, and connection errors instead of silently replacing them with embedded demo responses. This is a Vite build-time value: rebuild the web image after changing it. The backend's deterministic `REGONTOLOGY_AI_PROVIDER=fake` remains supported and is separate—it returns cited API responses without requiring an OpenAI key.

The GitHub Pages build explicitly sets `VITE_DEMO_MODE=true`; the Sites static demo leaves it unset and receives the same behavior from the frontend default. Both are API-independent mock previews. Do not reuse either static-demo build as the Docker/GHCR application image.

## OpenAI opt-in later

The initial `.env.local` contains:

```dotenv
REGONTOLOGY_AI_PROVIDER=fake
OPENAI_API_KEY=
```

This is the safe, no-network default and still exercises the citation/abstention UI with mock answers. After creating a key manually, edit only `.env.local`:

```dotenv
REGONTOLOGY_AI_PROVIDER=openai
OPENAI_API_KEY=replace-with-the-key-from-your-secret-store
```

Then run `pwsh ./scripts/dev.ps1 up`. Do not put the key in `.env.example`, Dockerfiles, Compose YAML, screenshots, logs, commits, or GitHub Actions variables. A production deployment must inject it from the institution's secret manager and must first approve the provider, region, retention, and regulation security classes.

## Container images and GHCR

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main` or `master`. It performs backend/frontend checks, mock-data syntax checks, repository secret/misconfiguration scanning, runtime-image vulnerability scanning, and a full Compose health smoke test.

After all gates pass on the default branch or a `v*` tag, the workflow publishes:

- `ghcr.io/begop/regontology-api`
- `ghcr.io/begop/regontology-web`

Published images include BuildKit SBOM and provenance attestations and are keylessly signed with GitHub OIDC. Tags include the branch, commit SHA, semantic version for `v*` releases, and `latest` on the default branch. The GitHub repository must allow Actions to write packages. Set each GHCR package to public if unauthenticated testers must pull it; otherwise testers must run `docker login ghcr.io` with a token that has `read:packages`.

### Security gate and exception recovery

High or critical findings block publication by default. A scanner database/network outage is handled with GitHub's **Re-run failed jobs** on the same push workflow and immutable commit; it is not bypassed with `continue-on-error`. (`workflow_dispatch` can validate a selected ref but intentionally does not publish it.) A genuine false positive or risk-accepted finding uses a reviewed, time-bounded entry in `.trivyignore.yaml`. Every exception must:

- narrow the suppression with `paths` or `purls` whenever Trivy provides them;
- include a `statement` naming the tracking issue, accountable owner, and compensating control;
- include an `expired_at` date no more than 30 days away;
- receive security-owner review and be removed as soon as a fixed base image or dependency is available.

This gives maintainers a deliberate recovery path without turning transient scanner failures into a permanent release block, while keeping unreviewed findings fail-closed. Secrets are never eligible for a release exception; rotate/remove the value and rerun the scan.

To run published images rather than local builds, place their desired tags in `.env.local`, then pull and start without building:

```dotenv
API_IMAGE=ghcr.io/begop/regontology-api:latest
WEB_IMAGE=ghcr.io/begop/regontology-web:latest
```

```powershell
docker compose --env-file .env.local pull api web
docker compose --env-file .env.local up --detach --no-build --wait --wait-timeout 240
```

## Public GitHub Pages mock UI

After the repository owner enables **Settings → Pages → Source: GitHub Actions**, a successful default-branch push deploys the mock-only UI to <https://begop.github.io/RegOntology/>. The separate `pages.yml` workflow runs only after the `CI and container release` workflow succeeds, so its deployment is downstream of `compose-smoke` but a Pages configuration failure cannot fail or block GHCR publication. It checks out the exact tested commit, repeats frontend type checking and component tests, builds with `VITE_BASE_PATH=/RegOntology/` and `VITE_DEMO_MODE=true`, uploads only `frontend/dist`, and deploys with GitHub's OIDC-backed Pages actions.

The Pages artifact contains `404.html` as a copy of the application shell so direct links such as `/RegOntology/ontology` can recover through React Router. The router obtains its basename from Vite's `/RegOntology/` base. This public page uses only the repository's fictional mock data, has no API key, database, live backend, ingestion capability, or persistent conversations. API failures are intentionally replaced with embedded demo responses on this preview only.

## Deployment boundary

This Compose profile is for local verification and sanitized development data. It is not the public hosting target. GitHub Pages exposes only the mock frontend; a remotely reachable full-stack URL still requires a deployment host and DNS/TLS credentials. Staging/production must additionally use the institution's IdP, a secret manager, private data networks, managed backup/PITR, ingress TLS/WAF/rate limits, signed-image verification, resource limits, and the approval gates in `docs/05-delivery/DEPLOYMENT.md`.

PostgreSQL is the canonical store. Neo4j remains a rebuildable projection; never restore it as the sole source of regulation data.
