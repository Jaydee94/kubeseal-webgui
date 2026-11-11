# Development

This guide covers running kubeseal-webgui on your laptop: API in Python, UI in
Node, plus an end-to-end loop on a local KinD cluster.

If you only want to install the released images on a real cluster, see
[installation.md](installation.md) instead.

## Prerequisites

- [Python 3.11 or newer](https://www.python.org/) (the API supports `>=3.11,<4.0`; the shipped container image runs the Python version of the digest-pinned `cgr.dev/chainguard/python` image, currently 3.15).
- [Poetry](https://python-poetry.org/) for managing the API's Python
  dependencies.
- [Node.js](https://nodejs.org/) — version `^20.19.0` or `>=22.12.0`
  (matches `ui/package.json`).
- [Docker](https://docs.docker.com/get-docker/) for building images.
- [kubectl](https://kubernetes.io/docs/tasks/tools/) and
  [Helm 3.8+](https://helm.sh/docs/intro/install/).
- [KinD](https://kind.sigs.k8s.io/) (optional, for the end-to-end loop).

## API (Python / FastAPI)

### Setup

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
```

`poetry install` installs both runtime and development dependencies declared
in `pyproject.toml` (including `pytest`, `ruff`, `mypy`, and `httpx` for
tests).

### Run locally

```bash
MOCK_ENABLED=true \
  poetry run uvicorn kubeseal_webgui_api.app:app \
    --port 5000 \
    --log-config config/logging_config.yaml
```

`MOCK_ENABLED=true` replaces the Kubernetes client and `kubeseal` invocations
with in-memory mocks, so you can develop without a cluster and without a
`kubeseal` binary. See [architecture.md](architecture.md#mock-mode) for
details.

Without mock mode the API runs `kubeseal --version` when it starts and
refuses to start if `KUBESEAL_BINARY` does not point to a working binary.

The API is then available at `http://localhost:5000`. Swagger UI is at
`http://localhost:5000/docs`.

### Tests

```bash
poetry run pytest -m "not cluster and not container"
```

This runs the unit tests. They need neither a cluster nor a `kubeseal`
binary: the sealing tests use a small stand-in script.

Markers defined in `pyproject.toml`:

- `cluster`: tests that need a real Kubernetes cluster.
- `container`: tests that need to run inside the API container.

A plain `poetry run pytest` also runs the tests with these markers, which
fail outside of their environment.

### Linting and formatting

```bash
poetry run ruff check .
poetry run black --check .
poetry run isort --check .
poetry run mypy kubeseal_webgui_api
```

`ruff`, `black`, `isort`, and `mypy` are configured in `pyproject.toml`.

## UI (Vue 3 / Vite)

### Setup

```bash
cd ui
npm install
```

This project uses npm. There is no `yarn.lock`; do not use Yarn.

### Run locally

```bash
npm run dev
```

Vite serves the SPA on `http://localhost:8080` with hot reload and proxies
the API routes to `http://localhost:5000` (see `server.proxy` in
`vite.config.mjs`). The API URL the SPA uses comes from `public/config.json`,
which `src/config.js` loads at startup; it is empty in development, so
requests go through the proxy. `.env.development` sets
`VITE_MOCK_NAMESPACES=true`, which makes the namespace list work without an
API.

### Build for production

```bash
npm run build
```

Outputs the production bundle to `ui/dist/`, which is what `Dockerfile.ui`
copies into the nginx image.

### Tests

```bash
npm test
```

runs the unit tests in `tests/unit/` with [Vitest](https://vitest.dev/).

The end-to-end tests in `tests/test_ui.py` drive a browser with Python
Playwright against the dev server; requests to the API are answered by the
tests themselves, so no API has to run:

```bash
pip install playwright pytest-playwright
playwright install chromium
npm run dev &        # the tests expect the dev server on port 8080
pytest tests/
```

### Linting and formatting

```bash
npm run lint           # eslint, auto-fixes where possible
npm run lint:check     # eslint, only reports
npm run format         # prettier, writes to src/ and tests/unit/
npm run format:check   # prettier, only reports
```

## Building the container images

```bash
docker build -f Dockerfile.api -t kubeseal-webgui-api:dev .
docker build -f Dockerfile.ui  -t kubeseal-webgui-ui:dev  .
```

Both builds are multi-stage:

- `Dockerfile.api` downloads the `kubeseal` binary in the first stage
  (version pinned via the `KUBESEAL_VERSION` build arg) and installs the
  Python package in the second.
- `Dockerfile.ui` runs `npm run build` in the first stage and serves the
  output via nginx in the second.

To run the API container against a real cluster's kubeconfig:

```bash
docker run --rm -t \
  -p 5000:5000 \
  -e MOCK_ENABLED=true \
  -e KUBESEAL_CERT=/tmp/cert.pem \
  kubeseal-webgui-api:dev
```

## End-to-end testing with KinD

A helper script bootstraps a complete local environment:

```bash
./kind-setup.sh
```

The script:

1. Creates a KinD cluster named `chart-testing` (dual-stack, ingress-ready).
2. Installs the Sealed Secrets controller into `kube-system`.
3. Installs `ingress-nginx`.
4. Builds the local API and UI images and loads them into the cluster.
5. Renders the Helm chart with snapshot tags and applies it.
6. Creates several test namespaces and `SealedSecret` objects, then exercises
   the API to verify the deployment.

After the script finishes, the UI is reachable at
`http://$(hostname -f):7180`.

## Continuous integration

GitHub Actions workflows live under
[`.github/workflows/`](../.github/workflows/). The most relevant ones are:

- `main.yml`: lint, tests, basic builds on every push and PR.
- `frontend-tests.yml`: UI test suite.
- `kind.yaml`: end-to-end test on a KinD cluster (its own inline steps,
  independent of `kind-setup.sh` above — the two aren't wired together, but
  cover equivalent ground).
- `codeql-analysis.yml`: static analysis.
- `container-security-scan.yml`: image vulnerability scan.
- `ghcr-build.yml`: build and push container images to GHCR on release.
- `helm-release.yml`: package and push the Helm chart to GHCR on release.
- `semantic-release.yml`: derive the next version and create a GitHub Release
  from Conventional Commit messages (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
