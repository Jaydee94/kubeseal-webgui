# Troubleshooting

Common problems and how to diagnose them. Each entry links to the relevant
section of the other docs.

## Auto-fetch certificate fails on startup

The API container logs an error like
`Failed to fetch the certificate from controller '...' in namespace '...' (exit code 1): cannot find sealed-secrets controller`
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
image this is `/kubeseal-webgui/bin/kubeseal`, baked in by `Dockerfile.api`. If you run the
API outside the container, you must install `kubeseal` locally and either:

- Place it at `/kubeseal-webgui/bin/kubeseal`, or
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
- The UI container not serving the expected `config.json` (check that the
  chart's ConfigMap contains the right `api.url`).

## OpenShift Route TLS mismatch

If the browser shows a certificate warning or you see HTTP/HTTPS confusion:

- `route.tls.enabled` controls whether the route terminates TLS at all.
- `route.tls.termination` must match what the upstream service expects.
  `edge` (the default) is correct for the bundled UI container, which speaks
  plain HTTP on port 8080.
- Make sure `api.url` uses the same scheme (`https://`) as the route, or
  the browser will block mixed content.

See [configuration.md](configuration.md#openshift-route).

## Pod rejected with `CreateContainerConfigError` or SCC-related admission errors

The chart sets a default `securityContext`/`containerSecurityContext` on the
pod and both containers. On OpenShift, the `restricted`/`restricted-v2` SCC
assigns its own `runAsUser`/`fsGroup`/`seLinuxOptions` from a
namespace-scoped range and can reject (or conflict with) a chart-supplied
one in some cluster configurations.

Disable the chart's own security context and let OpenShift's SCC fully own
it instead:

```bash
--set securityContext.enabled=false --set containerSecurityContext.enabled=false
```

See [configuration.md](configuration.md#security-context).

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

API log level is controlled by `api.loglevel` (default `INFO`). At startup the
API logs its effective settings (kubeseal version, binary and certificate
path, auto-fetch and mock mode). `DEBUG` additionally logs every kubeseal
invocation and one line per sealed key. Set `api.logformat: json` to get one
JSON object per line instead of text.

Cleartext secret values are never logged, at any level -- only secret names,
key names, namespaces and scopes.

Successful health probes (`GET /` from the kubelet) are left out of both
access logs; failing probes are logged.

### Following one request through all logs

Every request gets a request id. nginx generates it, writes it to its access
log (`request_id=...`), forwards it to the API as `X-Request-ID`, and the API
puts it in brackets into every log line of that request:

```text
# ui container
10.0.0.7 - - [...] "POST /secrets HTTP/1.1" 500 ... rt=0.041 urt=0.040 request_id=b3b50e39bc11f16ccbb286a000374417
# api container
... - kubeseal-webgui - ERROR - [b3b50e39bc11f16ccbb286a000374417] - Failed to seal secret 'foo' in namespace 'bar' with scope 'strict'.
```

The UI shows the same id in its error message (`... - request id b3b5...`), so
a user can report it and you can grep for it:

```bash
kubectl logs -n <namespace> -l app=kubeseal-webgui --all-containers | grep <request-id>
```

`rt` is the total request time seen by nginx, `urt` the time spent waiting for
the API.

### Browser console

The UI logs to the browser console with the prefix `[kubeseal-webgui]`:
failed requests (method, URL, HTTP status, duration, request id) and
unexpected errors. Request bodies and secret values are never logged. For
per-request debug output run this in the browser console and reload:

```js
localStorage.setItem("kubeseal-webgui:loglevel", "debug")
```

Valid levels are `debug`, `info` (default), `warn`, `error` and `silent`.
