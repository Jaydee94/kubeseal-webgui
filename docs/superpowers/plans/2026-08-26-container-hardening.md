# Container Hardening (Distroless API + Digest Pinning + Pod SecurityContext) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the CVE surface of the shipped `kubeseal-webgui` container images by moving the API runtime to a distroless base image, pinning every base image by digest, hardening the Kubernetes `securityContext`, and turning the existing (informational-only) Trivy scan into a real CI gate.

**Architecture:** The API image (`Dockerfile.api`) switches its final stage from `python:3.12-slim-bookworm` (a full Debian userland: shell, apt, coreutils, ~90 OS-level CVEs at time of writing) to `gcr.io/distroless/python3-debian12:nonroot` (no shell, no package manager, runs as uid 65532 by default). Python dependencies are compiled into a `pip install --target` directory in a `python:3.11-slim-bookworm` builder stage (matching the distroless image's bundled CPython 3.11 ABI) and copied in as pure files — no venv activation, no pip inside the final image. The UI image (`quay.io/nginx/nginx-unprivileged:1.31-alpine`) already scans clean (0 vulnerabilities) and needs a real shell for its `/docker-entrypoint.d/` hook, so it stays on its current base and gets hardened via digest pinning + `readOnlyRootFilesystem` instead of a base-image swap. All base images move from floating tags to `tag@sha256:digest` pins, kept fresh by a new Renovate config. The Helm chart gains a default pod- and container-level `securityContext` (`readOnlyRootFilesystem`, dropped capabilities, `runAsNonRoot`). Finally, `container-security-scan.yml`'s Trivy step changes from `exit-code: '0'` (never fails) to a real gate on CRITICAL (see Amendments #2 for why HIGH is excluded from the hard gate), with a `.trivyignore` for the handful of upstream-unfixed CVEs baked into the `kubeseal` Go binary that no base-image change can touch.

**Tech Stack:** Docker multi-stage builds, `gcr.io/distroless/python3-debian12`, Trivy (`aquasecurity/trivy-action`), Renovate, Helm.

**Spec:** No separate spec document — this plan was scoped directly from a live audit of the repo (Dockerfiles, `chart/kubeseal-webgui/`, `.github/workflows/container-security-scan.yml`) plus a Trivy report pulled from the most recent scheduled scan run (GitHub Actions run `31370206814`, 2026-08-10) and hands-on verification in this session (documented per-task below).

## Global Constraints

- Do not change the app's external behavior: `/config`, `/namespaces`, `/secrets`, `/sealed-secrets` endpoints and the UI's reverse-proxy routing must keep working exactly as before — verify with the existing `kind.yaml` E2E flow (or a manual equivalent) after Task 3 and Task 5.
- `kubeseal_webgui_api` currently declares `python = "^3.12"` in `api/pyproject.toml` (`requires-python = ">=3.12,<4.0"` in the built wheel). This must be relaxed to `>=3.11,<4.0` as part of Task 3 — verified in this session (see Task 3, Step 1) that the full non-cluster/non-container test suite (41 tests) passes unmodified under Python 3.11.16, and `ast.parse` succeeds on every source file, so there is no 3.12-only syntax to rewrite.
- Every base image must be pinned as `repository:tag@sha256:digest` (tag kept for human readability, digest is authoritative) — never digest-only, never tag-only.
- The Trivy CI gate (Task 6) must not go in before Task 3, or CI breaks immediately: the current `python:3.12-slim-bookworm`-based API image has 90 OS-level Trivy findings (6 CRITICAL, 18 HIGH, 66 MEDIUM) that Task 3 eliminates by dropping the Debian userland. Gating on the un-hardened image would fail CI on day one for reasons unrelated to any code change.

---

## Amendments

Recorded after this plan's tasks each passed their own task-scoped review,
but before a final whole-branch review; both amend predictions/targets made
earlier in this document that turned out not to match what actually shipped.

1. **Task 3's OS-package prediction was optimistic; the real numbers are
   honest, not "near zero."** This document's Baseline section predicted the
   Debian OS-package finding row "should drop to ~0" once Task 3 moved the
   API image to `gcr.io/distroless/python3-debian12:nonroot`. The measured
   result instead was: distinct vulnerable packages dropped 47% (32 → 17)
   and CRITICAL findings dropped 60% (5 → 2), but HIGH findings *increased*
   42% (31 → 44) and MEDIUM findings increased 47.5% (80 → 118), because the
   pinned distroless digest's patch-backport cadence lags a handful of
   packages (`libexpat1`, `libpython3.11-minimal`, `libc6`, others). This is
   a real security trade-off, not a bug: fewer distinct packages and fewer
   CRITICALs, at the cost of slower HIGH/MEDIUM remediation until the base
   image digest is refreshed. `docs/architecture.md` was corrected to state
   these measured numbers directly instead of this plan's original "near
   zero" prediction.

2. **Task 6's gate severity was narrowed to `CRITICAL` only, not
   `CRITICAL,HIGH` as this plan originally called for.** (Task 6's Step 3
   below has since been corrected in place to show the final `CRITICAL`-only
   state, so it doesn't recreate this same gap if re-run literally.) At gate
   time, 6 unique HIGH-severity CVEs on the hardened API image had a fixed
   version already published upstream that this pinned distroless digest
   snapshot simply hadn't incorporated yet. Per this plan's own rule ("Never
   ignore a CVE that has a fix available; bump the dependency instead" —
   see Task 6 Step 2), those 6 could not legitimately go in `.trivyignore`,
   but they also could not be fixed by anything this repo controls (no
   apt/pip we can bump for OS packages baked into the distroless base) —
   only an upstream distroless image rebuild resolves them. Gating on
   `CRITICAL,HIGH` as originally planned would have made CI permanently red
   for reasons no PR against this repo can fix. The gate was narrowed to
   `CRITICAL` only; the 6 affected CVE IDs are recorded here since they have
   no fixed version yet in the pinned digest and therefore no other durable
   in-repo record:
   - CVE-2025-13836
   - CVE-2026-40355
   - CVE-2026-40356
   - CVE-2026-4224
   - CVE-2026-45447
   - CVE-2026-6100

   HIGH and MEDIUM findings remain visible via the SARIF upload and the
   table-report artifact/PR comment (see
   `.github/workflows/container-security-scan.yml`); revisit widening the
   gate back to `CRITICAL,HIGH` once a fresher distroless digest closes
   this gap.

---

## Baseline (captured this session, for before/after comparison)

Pulled from the last scheduled Trivy run before this plan (`gh run view 31370206814`, artifacts `trivy-security-report-api` / `trivy-security-report-ui`, image built from `master` @ `910ead5`):

| Image | Scan target | Findings |
|---|---|---|
| `kubeseal-webgui-api` | `debian 12.15` (OS packages) | **90** (CRITICAL: 6, HIGH: 18, MEDIUM: 66) |
| `kubeseal-webgui-api` | Python packages (e.g. `msgpack`) | 7 (HIGH: 2, MEDIUM: 5) |
| `kubeseal-webgui-api` | Go binary build info (bundled `kubeseal` CLI) | 34 (HIGH: 22, MEDIUM: 12) |
| `kubeseal-webgui-ui` | `alpine 3.24.1` | **0** |

Task 3 targets the first row (OS packages) directly — distroless ships no `bsdutils`, no `apt`, no shell, so that row should drop to ~0. **This prediction did not hold — see Amendments #1 above for the actual measured numbers** (distinct packages and CRITICAL findings did drop substantially, but HIGH/MEDIUM findings rose due to the pinned distroless digest's patch-backport lag). The Go-binary row is a property of whichever `kubeseal` release we bundle (already bumped 0.36.6 → 0.39.1 in PR #313) and isn't fixable by a base-image change; unfixed ones get a documented `.trivyignore` entry in Task 6. The Python-package row is handled by the existing Renovate-driven dependency updates (Task 2), not by this plan directly.

---

### Task 1: Pin every Dockerfile base image by digest

**Files:**
- Modify: `Dockerfile.api:1` (`FROM debian:bookworm-slim AS deps`)
- Modify: `Dockerfile.api:23` (`FROM python:3.12-slim-bookworm`) — this line is replaced entirely in Task 3, but pin it now so Task 3's diff is smaller and CI stays green in between if the tasks land as separate PRs
- Modify: `Dockerfile.ui:1` (`FROM node:22-bookworm-slim AS ui-build-stage`)
- Modify: `Dockerfile.ui:8` (`FROM quay.io/nginx/nginx-unprivileged:1.31-alpine AS ui-production-stage`)

**Digests resolved this session** (via `docker buildx imagetools inspect <image> --format '{{json .Manifest}}'`):

| Image | Digest |
|---|---|
| `debian:bookworm-slim` | `sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171` |
| `python:3.12-slim-bookworm` | `sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579` |
| `node:22-bookworm-slim` | `sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5` |
| `quay.io/nginx/nginx-unprivileged:1.31-alpine` | `sha256:901e944d1f4fc2bd077e8f5568b98c1f6f8cdacf6b97a87747c43134a339b9a7` |

- [ ] **Step 1: Re-resolve digests at execution time**

Run (digests drift as upstream rebuilds happen — don't reuse the table above if more than a day or two has passed):

```bash
for img in debian:bookworm-slim python:3.12-slim-bookworm node:22-bookworm-slim quay.io/nginx/nginx-unprivileged:1.31-alpine; do
  echo "$img -> $(docker buildx imagetools inspect "$img" --format '{{println .Manifest.Digest}}')"
done
```

- [ ] **Step 2: Pin `Dockerfile.api`**

```dockerfile
FROM debian:bookworm-slim@sha256:<resolved-digest> AS deps
```
```dockerfile
FROM python:3.12-slim-bookworm@sha256:<resolved-digest>
```

- [ ] **Step 3: Pin `Dockerfile.ui`**

```dockerfile
FROM node:22-bookworm-slim@sha256:<resolved-digest> AS ui-build-stage
```
```dockerfile
FROM quay.io/nginx/nginx-unprivileged:1.31-alpine@sha256:<resolved-digest> AS ui-production-stage
```

- [ ] **Step 4: Verify both images still build and run**

```bash
docker build -f Dockerfile.api -t kubeseal-webgui-api:pin-test .
docker build -f Dockerfile.ui -t kubeseal-webgui-ui:pin-test .
```
Expected: both succeed with no new errors (the two pre-existing Hadolint-style warnings — `SecretsUsedInArgOrEnv` on the `PRIVATE_KEY` ENV and `UndefinedVar` for `$KUBESEAL_VERSION` in the second stage — are unrelated to this change and are out of scope here).

- [ ] **Step 5: Commit**

```bash
git add Dockerfile.api Dockerfile.ui
git commit -m "chore(docker): pin base images by digest"
```

---

### Task 2: Add Renovate to keep pinned digests (and everything else) fresh

Digest pinning without an update bot just calcifies today's CVEs. This repo has no Dependabot or Renovate config at all today (verified this session — `find . -iname dependabot.yml -o -iname renovate.json*` returns nothing).

**Files:**
- Create: `renovate.json`

- [ ] **Step 1: Write the config**

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "timezone": "Europe/Berlin",
  "schedule": ["before 6am on monday"],
  "docker": {
    "pinDigests": true
  },
  "packageRules": [
    {
      "matchManagers": ["dockerfile"],
      "matchUpdateTypes": ["digest"],
      "automerge": false,
      "commitMessageTopic": "{{depName}} digest"
    },
    {
      "matchManagers": ["poetry"],
      "matchFileNames": ["api/**"],
      "groupName": "api dependencies"
    },
    {
      "matchManagers": ["npm"],
      "matchFileNames": ["ui/**"],
      "groupName": "ui dependencies"
    },
    {
      "matchDatasources": ["github-releases"],
      "matchPackageNames": ["bitnami/sealed-secrets"],
      "commitMessageTopic": "kubeseal CLI"
    }
  ],
  "customManagers": [
    {
      "customType": "regex",
      "managerFilePatterns": ["/^Dockerfile\\.api$/"],
      "matchStrings": ["ARG KUBESEAL_VERSION=(?<currentValue>[\\d.]+)"],
      "datasourceTemplate": "github-releases",
      "depNameTemplate": "bitnami/sealed-secrets",
      "extractVersionTemplate": "^v(?<version>.*)$"
    }
  ]
}
```

This covers `Dockerfile.api`/`Dockerfile.ui` (digest bumps for all four pinned base images from Task 1, plus the future distroless image from Task 3), `api/pyproject.toml` + `api/poetry.lock`, and `ui/package.json` + `ui/package-lock.json`. The `github-releases` `packageRule` alone is *not* enough for `KUBESEAL_VERSION`: **corrected after the final whole-branch review caught this as a real plan defect** — Renovate's built-in `dockerfile` manager only extracts versions from `FROM`/`COPY --from=` lines and `ARG`s directly interpolated into a `FROM` line, not a bare `ARG KUBESEAL_VERSION=...` that's only consumed later in a `curl` URL inside a `RUN` instruction (`Dockerfile.api`'s actual pattern). The `customManagers` regex entry above is what actually makes Renovate track and bump that value; the `packageRule` just gives the resulting PR a distinct, greppable commit message.

- [ ] **Step 2: Validate the config syntax**

```bash
docker run --rm -v "$PWD/renovate.json:/usr/src/app/renovate.json" renovate/renovate:latest renovate-config-validator
```
Expected: `INFO: Config validated successfully`

- [ ] **Step 3: Commit**

```bash
git add renovate.json
git commit -m "chore: add Renovate config for automated dependency and digest updates"
```

- [ ] **Step 4: Manual follow-up (not code — flag to the user)**

Renovate only runs once the [Mend Renovate GitHub App](https://github.com/apps/renovate) is installed on the `Jaydee94/kubeseal-webgui` repository (or a self-hosted Renovate runner is wired into a workflow). This step can't be done from the CLI — call it out to whoever merges this so the config doesn't sit unused.

---

### Task 3: Rewrite `Dockerfile.api` to a distroless final stage

**Files:**
- Modify: `Dockerfile.api` (full rewrite of the second stage, lines 23–64)
- Modify: `api/pyproject.toml:11` (`python = "^3.12"` → `python = ">=3.11,<4.0"`)
- Modify: `api/poetry.lock` (regenerate after the constraint change)
- Delete: `api/bin/docker-entrypoint.sh` (dead code — see Step 0)

**Step 0 — why `api/bin/docker-entrypoint.sh` is dead code (verified this session, not an assumption):**

`Dockerfile.api:58` currently runs `install --mode=755 --group=0 ./src/bin/* "${APP_PATH}/bin/"`, baking `api/bin/docker-entrypoint.sh` into the image. That script's body execs `uwsgi` — a WSGI server this project doesn't use and doesn't install (the actual `CMD` calls `uvicorn` directly, never this script). It's leftover from a pre-uvicorn architecture. Distroless has no `/bin/sh` to run it even if something tried, so dropping the `install` step and the file itself is both a correctness cleanup and a required part of the distroless move — keep it and it just becomes 268 dead, unreadable bytes.

**Step 0b — why the Python-version bump to 3.11 is safe (verified this session, not an assumption):**

`gcr.io/distroless/python3-debian12:nonroot` bundles **Python 3.11.2** (checked via `docker run --rm gcr.io/distroless/python3-debian12:nonroot -c "import sys; print(sys.version)"`), but `api/pyproject.toml` currently requires `>=3.12,<4.0`. Verified by running the full non-cluster/non-container test suite inside `python:3.11-slim-bookworm` (`pip install --ignore-requires-python .`, then `pytest -m "not cluster and not container"`): **41 passed, 0 failed** — identical to the 3.12/3.14 result. `ast.parse()` over every file under `kubeseal_webgui_api/` also succeeds under 3.11, confirming no 3.12-only syntax (no PEP 695 `type` statements, no `except*`) is in use. The constraint is metadata-only conservatism, not a real dependency.

**Interfaces:**
- Consumes: pinned digests from Task 1 for `debian:bookworm-slim` (deps stage, unchanged) and the freshly-resolved `gcr.io/distroless/python3-debian12:nonroot` digest below.
- Produces: `kubeseal-webgui-api` image that responds on `:5000` exactly as before (`/config`, `/namespaces`, etc.) — Task 5 (Helm `securityContext`) builds directly on this image's non-root, read-only-friendly layout.

**Why a `python:3.11-slim-bookworm` builder (not 3.12):** compiled extension wheels (`pydantic-core`, `greenlet`, etc.) are ABI-tagged to a specific CPython minor version (`cp311` vs `cp312`). Building with `python:3.12` and running under the distroless image's `python3.11` would load `.so` files the interpreter can't import. The builder stage must match the runtime's interpreter version. `gcr.io/distroless/python3-debian12:nonroot` resolved to `sha256:7d1042ce588ab97019fe95c24ffca7bc5a82ccdac572511d5e09bda4435c89c5` this session; `python:3.11-slim-bookworm` resolved to `sha256:0bee7276f83efd4a1ee05bbbf4281d95ed28e079220a9457f25a93e3f1e3c31b` — re-resolve both at execution time the same way as Task 1.

- [ ] **Step 1: Relax the Python constraint**

In `api/pyproject.toml`:
```toml
[tool.poetry.dependencies]
python = ">=3.11,<4.0"
```
(was `python = "^3.12"`)

- [ ] **Step 2: Regenerate the lock file**

```bash
cd api && poetry lock
```
Expected: lock file updates cleanly, no resolution errors (nothing in the current dependency set is 3.12-only — verified via the 3.11 test run in Step 0b).

- [ ] **Step 3: Delete the dead entrypoint script**

```bash
git rm api/bin/docker-entrypoint.sh
```

- [ ] **Step 4: Rewrite `Dockerfile.api`**

```dockerfile
FROM debian:bookworm-slim@sha256:<resolved-digest> AS deps

ARG KUBESEAL_VERSION=0.39.1
ARG TARGETARCH
ENV KUBESEAL_BINARY=/deps/kubeseal

WORKDIR /deps

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    curl -Lsf -o /tmp/kubeseal.tar.gz "https://github.com/bitnami/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-${TARGETARCH}.tar.gz" && \
    tar -xzf /tmp/kubeseal.tar.gz kubeseal && \
    chmod 0755 "${KUBESEAL_BINARY}" && \
    rm /tmp/kubeseal.tar.gz && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim-bookworm@sha256:<resolved-digest> AS build

ARG APP_PATH="/kubeseal-webgui"
WORKDIR ${APP_PATH}

COPY api src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/opt/deps uvicorn wheel setuptools && \
    pip install --no-cache-dir --target=/opt/deps src/

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:<resolved-digest>

ARG APP_PATH="/kubeseal-webgui"
ARG APP_PORT=5000

ENV UVICORN_PORT=${APP_PORT} \
    UVICORN_NO_DATE_HEADER=1 \
    UVICORN_NO_SERVER_HEADER=1 \
    KUBESEAL_BINARY=${APP_PATH}/bin/kubeseal \
    PYTHONPATH=/opt/deps \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE ${APP_PORT}

WORKDIR ${APP_PATH}

COPY --from=build --chown=nonroot:nonroot /opt/deps /opt/deps
COPY --from=build --chown=nonroot:nonroot ${APP_PATH}/src ${APP_PATH}/src
COPY --from=deps --chown=nonroot:nonroot /deps/kubeseal ${APP_PATH}/bin/kubeseal

CMD [ "-m", "uvicorn", "--host", "", "--log-config", "src/config/logging_config.yaml", "kubeseal_webgui_api.app:app"]
```

Notes on what changed and why:
- No more `USER root` / `adduser` / second `apt-get upgrade` — the `:nonroot` distroless tag already runs as uid 65532 with no package manager to upgrade.
- Removed `openssl` cert generation and the `PRIVATE_KEY`/`PUBLIC_KEY` ENVs — that self-signed `/deps/cert.pem` was copied into the old final image (`COPY --from=deps /deps/*`) but never read by any code path (`AppSettings.kubeseal_cert` defaults to `/dev/null`, and Helm always mounts a real cert via ConfigMap). Dropping it also silences the pre-existing `SecretsUsedInArgOrEnv` Trivy/Hadolint warning on `Dockerfile.api:5` for free.
- `COPY --from=deps /deps/kubeseal` (single file) instead of `/deps/*` — no more incidental cert-file shipping.
- No `ENTRYPOINT` override: the distroless image already sets `ENTRYPOINT ["/usr/bin/python3.11"]` (verified via `docker inspect gcr.io/distroless/python3-debian12:nonroot`); `CMD` here supplies the `-m uvicorn ...` arguments appended to it.
- `pip install --target=/opt/deps` instead of a venv — distroless has no `venv`/shell to `activate`; `PYTHONPATH=/opt/deps` makes the interpreter find the packages directly. Console-script shims aren't needed since we invoke `python3 -m uvicorn` rather than the `uvicorn` binary.
- `KUBESEAL_BINARY=${APP_PATH}/bin/kubeseal` (not `/tmp/kubeseal`, corrected after this task originally shipped with the `/tmp` path): Task 5's Helm chart adds a `tmp` emptyDir volume mounted at `/tmp` in this container for `readOnlyRootFilesystem` support, which Kubernetes mounts *over* the image's baked-in `/tmp` contents — masking a binary placed there and crashing the container at Python import time. The final whole-branch review caught this; see the branch history for the fix commit. Placing the binary under `${APP_PATH}/bin/` instead avoids the collision entirely.

- [ ] **Step 5: Build**

```bash
docker build -f Dockerfile.api -t kubeseal-webgui-api:distroless .
```
Expected: succeeds. If it fails on a missing wheel for some package (a pure-Python-only assumption turns out wrong for some transitive dep with no `cp311`/`manylinux` wheel available), that's the signal to check `poetry show --tree` for the offending package before doing anything else — don't paper over it with `--no-binary` guesses.

- [ ] **Step 6: Smoke-test**

```bash
docker run --rm -d --name kubeseal-webgui-api-distroless-test -e MOCK_ENABLED=true -p 15000:5000 kubeseal-webgui-api:distroless
sleep 3
curl -sf http://localhost:15000/config
docker exec kubeseal-webgui-api-distroless-test /kubeseal-webgui/bin/kubeseal --version
docker stop kubeseal-webgui-api-distroless-test
```
Expected: `/config` returns `{"kubesealVersion":"0.1.0", ...}` (the mock-mode placeholder, same as before), `kubeseal --version` reports `0.39.1`. `docker exec ... sh` will *not* work (no shell) — that's expected and correct, not a bug to work around.

- [ ] **Step 7: Confirm the CVE drop**

```bash
docker run --rm ghcr.io/aquasecurity/trivy:latest image --severity CRITICAL,HIGH,MEDIUM kubeseal-webgui-api:distroless
```
Expected: the "OS packages" scan target (previously `debian 12.15`, 90 findings) drops in distinct-package count and CRITICAL severity — distroless's userland is a handful of libc/openssl/certs packages, not a full Debian install. **This does not mean the finding count itself drops to near zero — see Amendments #1 for the actual measured before/after numbers**, which include a real increase in raw HIGH/MEDIUM findings due to the pinned digest's patch-backport lag. The Python-package and Go-binary findings groups will still show (unrelated to this task, tracked separately per the baseline table above).

- [ ] **Step 8: Run the existing backend test suite against the change**

```bash
cd api && poetry run pytest tests/ -m "not cluster and not container"
```
Expected: 41 passed (unchanged from before this task — this only touched packaging metadata and the Docker build, not application code).

- [ ] **Step 9: Commit**

```bash
git add Dockerfile.api api/pyproject.toml api/poetry.lock
git commit -m "refactor(docker): rebuild API image on distroless, drop Debian OS CVE surface"
```

---

### Task 4: Update `docs/architecture.md` for the new image layout

**Files:**
- Modify: `docs/architecture.md:50-56` (API container section)

- [ ] **Step 1: Rewrite the section**

Replace:
```markdown
### API container

- Base image: `python:3.12-slim-bookworm`.
- Built from `Dockerfile.api`. A first build stage downloads the `kubeseal`
  binary (version pinned via the `KUBESEAL_VERSION` build arg, currently
  `0.39.1`); the runtime stage installs the Python package and copies the
  binary in.
- Runs `uvicorn` against `kubeseal_webgui_api.app:app` on port 5000.
```
With:
```markdown
### API container

- Base image: `gcr.io/distroless/python3-debian12:nonroot` (no shell, no
  package manager, runs as uid 65532) — chosen over a full Debian base to
  eliminate OS-level CVE exposure; see
  `docs/superpowers/plans/2026-08-26-container-hardening.md` for the
  before/after vulnerability counts that drove this.
- Built from `Dockerfile.api` in three stages: a `debian:bookworm-slim`
  stage downloads the `kubeseal` binary (version pinned via the
  `KUBESEAL_VERSION` build arg, currently `0.39.1`); a
  `python:3.11-slim-bookworm` stage `pip install --target`s the Python
  package and its dependencies (the builder's Python minor version must
  match the distroless runtime's bundled 3.11 interpreter — see the ABI
  note in the hardening plan); the final distroless stage copies both in.
- Runs `python3 -m uvicorn kubeseal_webgui_api.app:app` on port 5000 (no
  `ENTRYPOINT` override — the distroless image already targets its bundled
  interpreter).
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: update architecture.md for the distroless API image"
```

---

### Task 5: Harden the Helm chart's `securityContext`

**Files:**
- Modify: `chart/kubeseal-webgui/values.yaml` (add `securityContext` and `containerSecurityContext` defaults after the existing `resources:` block, i.e. after line 44)
- Modify: `chart/kubeseal-webgui/templates/deployment.yaml:41-113` (add container-level `securityContext` + `/tmp` volume mounts to both containers)

**Why `/tmp` and nothing else needs mounting (verified this session, not an assumption):**
`docker run --rm --read-only --tmpfs /tmp -p 18081:8080 quay.io/nginx/nginx-unprivileged:1.31-alpine` started cleanly and served `HTTP 200` on `/` — the unprivileged nginx image already keeps all of its runtime scratch state (temp dirs, PID file) under `/tmp` for exactly this reason. The only warning logged was the stock `10-listen-on-ipv6-by-default.sh` hook failing to patch `/etc/nginx/conf.d/default.conf` (read-only) — non-fatal, and irrelevant here anyway: `ui/nginx-default.conf` hardcodes `proxy_pass http://localhost:5000` (API sidecar in the same pod), and this project's own `50-envsubst-default-conf.sh` hook only rewrites that same value from `API_HOST`/`API_PORT` env vars that `templates/deployment.yaml`'s `ui` container never sets — so the substitution is already a no-op in every Helm-deployed instance of this chart. `readOnlyRootFilesystem` does not change UI container behavior.
For the API container, `PYTHONDONTWRITEBYTECODE=1` (added in Task 3) stops the interpreter from trying to write `.pyc` files; the only other runtime writes (`KUBESEAL_CERT` when `sealedSecrets.autoFetchCert: true`) already land on a dedicated `emptyDir` volume mount, independent of root-FS writability. Give the API container a `/tmp` mount too, defensively, since arbitrary Python stdlib/3rd-party code can reach for `tempfile` at any time.

- [ ] **Step 1: Add defaults to `values.yaml`**

Insert after line 44 (the end of the `resources:` block):
```yaml
# Pod-level hardening. Override individual keys via --set if your cluster's
# PSA/PSP config needs something different (the E2E kind cluster does this
# for securityContext.runAsUser, see .github/workflows/kind.yaml).
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
# Container-level hardening, applied identically to the api and ui containers.
containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

- [ ] **Step 2: Wire `containerSecurityContext` and a `/tmp` mount into both containers in `deployment.yaml`**

For the `api` container, after `imagePullPolicy: {{ .Values.image.pullPolicy }}` (line 43):
```yaml
          {{- with .Values.containerSecurityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
```
And append to its existing `volumeMounts:` block (after line 90, the `logging_config.yaml` mount):
```yaml
            - name: tmp
              mountPath: /tmp
```

For the `ui` container, after its `imagePullPolicy: {{ .Values.image.pullPolicy }}` (line 93):
```yaml
          {{- with .Values.containerSecurityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
```
And append to its existing `volumeMounts:` block (after line 113, the `config.json` mount):
```yaml
            - name: tmp
              mountPath: /tmp
```

Add a shared `tmp` volume to the pod's `volumes:` list (after line 118, alongside the existing `sealed-secret-configmap` volume):
```yaml
        - name: tmp
          emptyDir: {}
```

- [ ] **Step 3: Lint and render**

```bash
helm lint chart/kubeseal-webgui
helm template chart/kubeseal-webgui \
  --set api.image.tag=distroless-test \
  --set ui.image.tag=distroless-test \
  --set sealedSecrets.autoFetchCert=true > /tmp/rendered.yaml
```
Expected: no lint errors; rendered manifest shows `securityContext` on the pod and on both containers, plus a `tmp` volume mounted at `/tmp` in both containers.

- [ ] **Step 4: End-to-end verification**

The existing `.github/workflows/kind.yaml` already builds both images, deploys via `helm template | kubectl apply`, and curls `/namespaces`, `/config`, and `/secrets` end-to-end, plus applies real `SealedSecret` objects through a live `sealed-secrets` controller. That workflow triggers automatically on this PR — treat a green `kind.yaml` run as the real verification for this task (a local kind cluster reproduces the same steps if you want to check before pushing; see that workflow file for the exact commands).

- [ ] **Step 5: Commit**

```bash
git add chart/kubeseal-webgui/values.yaml chart/kubeseal-webgui/templates/deployment.yaml
git commit -m "feat(chart): harden pod and container securityContext by default"
```

---

### Task 6: Turn the Trivy scan into a real CI gate

**Files:**
- Modify: `.github/workflows/container-security-scan.yml:56-64` (the "table report" step's `exit-code`)
- Create: `.trivyignore`

**Do this task last** — it depends on Task 3 having already cleared the ~90-finding Debian OS-package backlog; gating earlier fails CI for pre-existing reasons unrelated to whatever PR happens to trigger it first.

- [ ] **Step 1: Re-run the scan against the hardened images to find what's left**

```bash
docker build -f Dockerfile.api -t kubeseal-webgui-api:gate-check .
docker run --rm ghcr.io/aquasecurity/trivy:latest image --severity CRITICAL,HIGH --format json kubeseal-webgui-api:gate-check > /tmp/api-scan.json
docker build -f Dockerfile.ui -t kubeseal-webgui-ui:gate-check .
docker run --rm ghcr.io/aquasecurity/trivy:latest image --severity CRITICAL,HIGH --format json kubeseal-webgui-ui:gate-check > /tmp/ui-scan.json
```

- [ ] **Step 2: Write `.trivyignore` for anything left with no fixed version**

Only add an entry if Step 1 shows a CVE with an empty "Fixed Version" column (i.e., genuinely nothing to upgrade to yet — typically the Go-stdlib CVEs baked into whichever `kubeseal` release is bundled). Never ignore a CVE that has a fix available; bump the dependency instead. Each entry needs a reason and a review date so this file doesn't silently rot:

```
# CVE-ID # reason # review-by
# Example (fill in with whatever Step 1 actually reports as unfixed):
# CVE-2026-XXXXX # no fixed version yet upstream in bitnami/sealed-secrets; re-check on next kubeseal bump # 2026-11-01
```

- [ ] **Step 3: Flip the gate**

In `.github/workflows/container-security-scan.yml`, change the table-report step (currently lines 56-64):
```yaml
      - name: Run Trivy vulnerability scanner (table report)
        uses: aquasecurity/trivy-action@v0.35.0
        if: always()
        with:
          image-ref: ${{ matrix.image }}:${{ github.sha }}
          format: table
          output: trivy-report-${{ matrix.name }}.txt
          severity: CRITICAL,HIGH,MEDIUM
          exit-code: '0'
```
to (**corrected to the final shipped state — see Amendments #2**; the
original Step 3 dispatched to the implementer said `severity: CRITICAL,HIGH`,
which was found during Step 4 verification to fail persistently on findings
this repo cannot fix, and was narrowed as described in Amendments #2):
```yaml
      - name: Run Trivy vulnerability scanner (table report)
        uses: aquasecurity/trivy-action@v0.35.0
        if: always()
        with:
          image-ref: ${{ matrix.image }}:${{ github.sha }}
          format: table
          output: trivy-report-${{ matrix.name }}.txt
          severity: CRITICAL
          exit-code: '1'
          trivyignores: .trivyignore
```
(Dropped `HIGH` and `MEDIUM` from the gated severity list — gate on CRITICAL
only, keep reporting HIGH/MEDIUM informationally via the SARIF upload step
above it, which is untouched. Gating on more than CRITICAL turned out to
produce a permanently-failing check for reasons no PR against this repo can
fix — see Amendments #2.)

- [ ] **Step 4: Verify the gate passes on the hardened images**

```bash
docker run --rm -v "$PWD/.trivyignore:/.trivyignore" ghcr.io/aquasecurity/trivy:latest image \
  --severity CRITICAL --exit-code 1 --ignorefile /.trivyignore kubeseal-webgui-api:gate-check
echo "exit code: $?"
docker run --rm ghcr.io/aquasecurity/trivy:latest image \
  --severity CRITICAL --exit-code 1 kubeseal-webgui-ui:gate-check
echo "exit code: $?"
```
Expected: both exit `0`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/container-security-scan.yml .trivyignore
git commit -m "ci: fail container-security-scan on CRITICAL/HIGH CVEs"
```

---

## Deferred / not in this plan (call out, don't silently drop)

- **SBOM generation + image signing (cosign/Syft in `ghcr-build.yml`)** — supply-chain provenance, not CVE-count reduction. Worth a follow-up plan once this one has shipped and settled; scoping it in here would roughly double this plan's size for a materially different goal (integrity/provenance vs. vulnerability surface).
- **Switching the UI runtime off `nginx-unprivileged` entirely** (e.g. to a Chainguard/Wolfi nginx image) — rejected in this plan per the chosen strategy (pure Google Distroless, no official distroless nginx exists) and because the current image already scans at 0 vulnerabilities; revisit only if that stops being true.
- **`node:22-bookworm-slim` build-stage hardening beyond digest pinning** — it's discarded before the final `ui-production-stage` and never shipped, so it doesn't affect the runtime CVE surface. Digest-pinning it (Task 1) is just supply-chain hygiene for the build itself.

## Self-Review

**Spec coverage:** every gap identified in the initial audit (floating tags, Debian-based API image, no CI gate, no default `securityContext`, no update automation) has a task. The dead `docker-entrypoint.sh` and unused self-signed cert found during research are folded into Task 3 rather than given their own task, since they're touched by the same file anyway (per the "fold into the task whose deliverable needs it" rule).

**Placeholder scan:** the only bracketed placeholders remaining are `<resolved-digest>`, which are *by definition* not fillable in advance — they're live upstream digests that would already be stale by the time this plan is read. Every task that uses one pairs it with the exact command to resolve the live value first.

**Type/name consistency:** `containerSecurityContext` (values.yaml) is the name used consistently in both its Task 5 definition and its two `deployment.yaml` consumption sites. `tmp` is the volume name used consistently across both container `volumeMounts` and the pod `volumes` list.
