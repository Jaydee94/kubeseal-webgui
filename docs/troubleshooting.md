# Troubleshooting

Common problems and how to diagnose them. Each entry links to the relevant
section of the other docs.

## Auto-fetch certificate fails on startup

The API container logs an error like
`Error in run_kubeseal: cannot find sealed-secrets controller`
or hangs in `CrashLoopBackOff` shortly after start.

Most common causes:

- **Controller name or namespace mismatch.** Confirm with
  `kubectl get deploy -A | grep sealed-secrets` that the Sealed Secrets
  controller deployment name and namespace match your `sealedSecrets.controllerName`
  and `sealedSecrets.controllerNamespace` values.
- **Default mismatch.** The API code defaults the controller namespace to
  `sealed-secrets`, but the Helm chart sets it to `kube-system`. If you set
  `KUBESEAL_AUTOFETCH=true` directly (without going through the chart), make
  sure you also set `KUBESEAL_CONTROLLER_NAMESPACE` to the right value.
- **Missing RBAC.** If you set `customServiceAccountName`, the service
  account must be able to talk to the Sealed Secrets controller. Use the
  bundled `ServiceAccount` (leave `customServiceAccountName` empty) or grant
  equivalent permissions yourself.

See [configuration.md](configuration.md#sealed-secrets-controller).

## `kubeseal binary not found` or 500 errors on `POST /secrets`

The API expects `kubeseal` at `KUBESEAL_BINARY`. In the published container
image this is `/tmp/kubeseal`, baked in by `Dockerfile.api`. If you run the
API outside the container, you must install `kubeseal` locally and either:

- Place it at `/tmp/kubeseal`, or
- Set `KUBESEAL_BINARY` to the actual path before starting the API.

See [development.md](development.md#api-python--fastapi).

## UI loads but says "API unreachable"

The browser fetches `config.json` at startup to discover the API URL. If
`api.url` is wrong, the SPA cannot reach the API.

- If you access the UI via an ingress, set `api.url` to the **public** URL
  the browser uses, not the in-cluster service name.
- Inside a single-pod deployment, the UI's nginx reverse-proxies API paths
  to `localhost:5000` automatically, so `api.url` only needs to match the
  public hostname.

See [configuration.md](configuration.md#ui-configuration).

## Ingress returns 502

The pod has both UI and API containers. If only one of them is `Ready`, the
service has no healthy endpoint.

```bash
kubectl describe pod -n <namespace> -l app=kubeseal-webgui
```

Look for:

- The API container failing to fetch the certificate (see above).
- The UI container failing to render `config.json` (check the entrypoint
  hook logs for `api.url` being unset).

## OpenShift Route TLS mismatch

If the browser shows a certificate warning or you see HTTP/HTTPS confusion:

- `route.tls.enabled` controls whether the route terminates TLS at all.
- `route.tls.termination` must match what the upstream service expects.
  `edge` (the default) is correct for the bundled UI container, which speaks
  plain HTTP on port 8080.
- Make sure `api.url` uses the same scheme (`https://`) as the route, or
  the browser will block mixed content.

See [configuration.md](configuration.md#openshift-route).

## Mock mode not engaging

If you set `MOCK_ENABLED=true` but the API still tries to talk to a real
cluster:

- The variable must be set **at process start**, not later. Restart the API.
- Casing matters less than you might think (the API treats anything except
  the literal string `true` (case-insensitive) as `false`).

See [architecture.md](architecture.md#mock-mode).

## Where to find logs

```bash
kubectl logs -n <namespace> -l app=kubeseal-webgui -c api
kubectl logs -n <namespace> -l app=kubeseal-webgui -c ui
```

API log level is controlled by `api.loglevel` (default `INFO`). Set it to
`DEBUG` to get verbose startup output, including the resolved certificate
path and the controller name/namespace used by auto-fetch.
