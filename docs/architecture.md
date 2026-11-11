# Architecture

kubeseal-webgui is a thin web frontend around the
[`kubeseal`](https://github.com/bitnami/sealed-secrets) CLI. It runs as
two containers in a single pod and never stores anything: secrets are encrypted
in-flight using the Sealed Secrets controller's public certificate, and the
encrypted result is returned to the browser as JSON.

## Overview

```mermaid
flowchart LR
    Browser -->|HTTPS / static files + /api/*| Nginx
    subgraph Pod["Pod (kubeseal-webgui)"]
        Nginx["UI container<br/>nginx + Vue SPA"]
        API["API container<br/>FastAPI + kubeseal binary"]
        Nginx -->|reverse proxy| API
    end
    API -.->|kubectl list namespaces<br/>kubectl get sealedsecrets| K8s["Kubernetes API"]
    API -.->|fetch public cert<br/>(optional, on startup)| Controller["Sealed Secrets controller"]
```

The browser only ever talks to the UI container. The UI container's nginx
reverse-proxies a fixed set of paths to the API container on `localhost:5000`.
The API container shells out to the local `kubeseal` binary to perform the
encryption.

## Components

### UI container

- Base image: [`cgr.dev/chainguard/nginx`](https://images.chainguard.dev/directory/image/nginx/overview)
  (Chainguard hardened image on Wolfi: no shell, no package manager, runs as
  uid 65532, rebuilt daily and typically free of known CVEs). Pinned by
  digest; Renovate bumps the digest.
- Built from `Dockerfile.ui`. The build stage compiles the Vue 3 + Vuetify 4
  SPA with Vite; the runtime stage copies the static bundle into the nginx
  image together with [`ui/nginx.conf`](../ui/nginx.conf), which moves the
  PID file and all temp paths to `/tmp` so the container runs with
  `readOnlyRootFilesystem`.
- Listens on port 8080 (IPv4 and IPv6).
- Reverse-proxies the API routes to the in-pod API:

  ```nginx
  location ~ /(sealed-secrets|secrets|namespaces|config|docs|openapi.json)(/.*)?$ {
      proxy_pass http://localhost:5000;
  }
  ```

  See [`ui/nginx-default.conf`](../ui/nginx-default.conf).
- The SPA fetches `config.json` at startup to find the API. The Helm chart
  renders it from `api.url` into a ConfigMap that is mounted over
  `/usr/share/nginx/html/config.json`, so the same image can be deployed to
  any environment without rebuilding. The image has no shell and therefore
  no entrypoint hooks: to point the reverse proxy at a different API
  upstream outside the chart, mount your own server block over
  `/etc/nginx/conf.d/default.conf`.

### API container

- Base image: [`cgr.dev/chainguard/python`](https://images.chainguard.dev/directory/image/python/overview)
  (Chainguard hardened image on Wolfi: no shell, no package manager, runs as
  uid 65532, rebuilt daily and typically free of known CVEs). The free tier
  only publishes the floating `latest`/`latest-dev` tags, so both are pinned
  by digest and Renovate bumps them together.
- Built from `Dockerfile.api` in three stages: a `debian:bookworm-slim`
  stage downloads the official `kubeseal` release binary and verifies its
  checksum (version pinned via the `KUBESEAL_VERSION` build arg); a
  `cgr.dev/chainguard/python:latest-dev` stage `pip install --target`s the
  Python package and its runtime dependencies (it must be the -dev variant of
  the same image as the runtime, because compiled wheels are tied to one
  CPython minor version); the final stage copies both in and runs an
  import smoke test at build time that fails on an ABI mismatch.
- Runs `python -m uvicorn kubeseal_webgui_api.app:app` on port 5000 (no
  `ENTRYPOINT` override — the base image already targets its bundled
  interpreter).
- On startup, optionally fetches the controller's public certificate (see
  `fetch_sealed_secrets_cert` in
  [`api/kubeseal_webgui_api/app_config.py`](../api/kubeseal_webgui_api/app_config.py)).

### Sealed Secrets controller (external)

The Sealed Secrets controller is **not** part of this chart. It must already
be installed in the target cluster. kubeseal-webgui only needs its public
certificate to encrypt secrets; only the controller can decrypt them.

## Request flow: sealing a secret

1. The user opens the UI in a browser. The SPA loads `config.json` to discover
   the API URL.
2. The SPA calls `GET /namespaces` to populate the namespace selector.
3. The user enters a secret name, namespace, scope, and one or more
   key/value pairs, then submits.
4. The SPA sends `POST /secrets` with the payload as JSON.
5. The API container writes a temporary YAML representation of the secret and
   invokes `kubeseal --raw` (or equivalent) using the public certificate at
   `KUBESEAL_CERT`.
6. The API returns the encrypted key/value pairs as JSON. The SPA renders
   them as a copy-paste-ready `SealedSecret` manifest.

No secret data is ever persisted by kubeseal-webgui. The encryption is
deterministic only with respect to the controller's key pair: the same
plaintext encrypted twice produces two different ciphertexts, but both are
decryptable by the controller.

## API endpoints

| Method | Path | Description | Source |
|---|---|---|---|
| `GET` | `/` | Health check. Returns `{"status": "Kubeseal-WebGui API"}`. | `app.py` |
| `GET` | `/config` | Reports the `kubeseal` binary version and other static config. | `routers/config.py` |
| `GET` | `/namespaces` | Lists namespaces visible to the service account. | `routers/kubernetes.py` |
| `GET` | `/sealed-secrets/{namespace}` | Lists existing `SealedSecret` objects in a namespace. Only enabled when `enableExistingSealedSecretLoading=true`. | `routers/kubernetes.py` |
| `POST` | `/secrets` | Encrypts a payload and returns the encrypted key/value pairs. | `routers/kubeseal.py` |

OpenAPI documentation is served at `/docs` (Swagger UI) and `/openapi.json`
when the API is reachable.

## RBAC

The chart ships a `ClusterRole` named `kubeseal-webgui-list-namespaces`
([`clusterrole.yaml`](../chart/kubeseal-webgui/templates/clusterrole.yaml))
that grants:

- `list` on core `namespaces`
- `get`, `list` on `sealedsecrets.bitnami.com`

If you bring your own `ServiceAccount` via `customServiceAccountName`, you
must grant equivalent permissions yourself.

## Mock mode

Setting `MOCK_ENABLED=true` swaps the Kubernetes client and `kubeseal`
invocations for in-memory mocks
(see `mock_namespace_resolver.py` and `mock_sealed_secret_resolver.py` next
to `routers/kubernetes.py`). This lets you run the API locally without a
cluster or controller — useful when developing the UI or the API itself.

## Image distribution

Container images are published to the GitHub Container Registry:

- `ghcr.io/jaydee94/kubeseal-webgui/api`
- `ghcr.io/jaydee94/kubeseal-webgui/ui`

The Helm chart is published as an OCI artifact to
`oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui`.
