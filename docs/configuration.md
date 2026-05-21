# Configuration

This page is the authoritative reference for everything you can tune in
kubeseal-webgui: Helm values, API environment variables, and the UI's
runtime configuration.

The values listed here are kept in sync with the actual defaults in
[`chart/kubeseal-webgui/values.yaml`](../chart/kubeseal-webgui/values.yaml).
If anything looks out of date, the YAML file is the source of truth.

## Helm values

### Image and replicas

| Parameter | Description | Default |
|---|---|---|
| `replicaCount` | Number of pod replicas. | `1` |
| `annotations` | Additional pod annotations. | `{}` |
| `api.image.repository` | API image repository. | `ghcr.io/jaydee94/kubeseal-webgui/api` |
| `api.image.tag` | API image tag. | Matches chart `appVersion` (see [Chart.yaml](../chart/kubeseal-webgui/Chart.yaml)). |
| `ui.image.repository` | UI image repository. | `ghcr.io/jaydee94/kubeseal-webgui/ui` |
| `ui.image.tag` | UI image tag. | Matches chart `appVersion` (see [Chart.yaml](../chart/kubeseal-webgui/Chart.yaml)). |
| `image.pullPolicy` | Image pull policy. | `Always` |
| `imagePullSecrets` | Image pull secrets for private registries. | `[]` |
| `nameOverride` | Override the chart name component of object names. | `""` |
| `fullnameOverride` | Override the full release name. | `""` |
| `displayName` | Optional display name for this kubeseal-webgui instance. | `""` |

### Service account and RBAC

| Parameter | Description | Default |
|---|---|---|
| `customServiceAccountName` | Use an existing `ServiceAccount` instead of the one shipped with the chart. The account must be able to list namespaces. Leave empty to use the bundled `ServiceAccount` and `ClusterRole`. | `""` |

The bundled `ClusterRole`
([`clusterrole.yaml`](../chart/kubeseal-webgui/templates/clusterrole.yaml))
grants `list` on `namespaces` and `get`/`list` on
`sealedsecrets.bitnami.com`.

### Networking

#### Ingress

| Parameter | Description | Default |
|---|---|---|
| `ingress.enabled` | Create an `Ingress` object. | `false` |
| `ingress.annotations` | Additional annotations on the `Ingress`. | `{}` |
| `ingress.ingressClassName` | `ingressClassName` to set on the `Ingress`. | `""` |
| `ingress.hostname` | Hostname for the ingress route. | `kubeseal-webgui.example.com` |
| `ingress.tls.enabled` | Enable TLS on the ingress route. | `false` |
| `ingress.tls.secretName` | Name of the TLS secret (must exist in the release namespace). | `""` |

#### OpenShift Route

| Parameter | Description | Default |
|---|---|---|
| `route.enabled` | Create an OpenShift `Route`. | `false` |
| `route.hostname` | Hostname of the route. Empty lets OpenShift assign one. | `""` |
| `route.tls.enabled` | Enable TLS on the route. | `true` |
| `route.tls.termination` | TLS termination mode (`edge`, `reencrypt`, `passthrough`). | `edge` |
| `route.tls.insecureEdgeTerminationPolicy` | What to do with HTTP traffic (`None`, `Allow`, `Redirect`). | `None` |

### Sealed-Secrets controller

| Parameter | Description | Default |
|---|---|---|
| `sealedSecrets.autoFetchCert` | Fetch the controller's public certificate on API startup. | `false` |
| `sealedSecrets.controllerName` | Deployment name of the Sealed Secrets controller. | `sealed-secrets-controller` |
| `sealedSecrets.controllerNamespace` | Namespace of the Sealed Secrets controller. | `kube-system` |
| `sealedSecrets.cert` | Public certificate of the controller, provided inline (used when `autoFetchCert=false`). | `""` |
| `enableExistingSealedSecretLoading` | UI feature flag: allow importing keys from existing `SealedSecret` objects in a namespace. | `false` |

### Resources, scheduling, and API options

| Parameter | Description | Default |
|---|---|---|
| `resources.limits.cpu` | CPU limit. | unset |
| `resources.limits.memory` | Memory limit. | `256Mi` |
| `resources.requests.cpu` | CPU request. | `20m` |
| `resources.requests.memory` | Memory request. | `256Mi` |
| `tolerations` | Pod tolerations. | `[]` |
| `affinity` | Pod affinity rules. | `{}` |
| `nodeSelector` | Pod node selector. | `{}` |
| `api.url` | Public URL of the API as seen by the browser. Rendered into the UI's `config.json` ConfigMap. | `http://localhost:8080` |
| `api.loglevel` | Log level for the API container (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `api.environment` | Additional environment variables for the API container as a map. | `{}` |

## API environment variables

These are read directly by the API process and can be set via
`api.environment` in the Helm values. Source:
[`api/kubeseal_webgui_api/app_config.py`](../api/kubeseal_webgui_api/app_config.py).

| Variable | Description | Default |
|---|---|---|
| `KUBESEAL_BINARY` | Absolute path to the `kubeseal` executable inside the container. | `/tmp/kubeseal` (set in `Dockerfile.api`) |
| `KUBESEAL_CERT` | Path to the controller's public certificate. | `/kubeseal-webgui/cert/kubeseal-cert.pem` |
| `KUBESEAL_AUTOFETCH` | Set to `true` to fetch the certificate from the controller on startup. Set by the chart when `sealedSecrets.autoFetchCert=true`. | `false` |
| `KUBESEAL_CONTROLLER_NAME` | Deployment name of the Sealed Secrets controller (used when auto-fetching). | `sealed-secrets-controller` |
| `KUBESEAL_CONTROLLER_NAMESPACE` | Namespace of the Sealed Secrets controller (used when auto-fetching). | `sealed-secrets` in the API code, overridden to match `sealedSecrets.controllerNamespace` by the chart. |
| `MOCK_ENABLED` | Replace the Kubernetes client and `kubeseal` invocations with in-memory mocks. Useful for local development without a cluster. | `false` |

## UI configuration

The UI is a static SPA. At container startup, an entrypoint hook renders
`api.url` into a `config.json` file served alongside the bundled HTML, so the
browser knows where to find the API.

You only need to set one value:

- `api.url`: the public URL of the API as the browser sees it. With the
  bundled chart this is usually the same URL as the UI itself, because the
  UI's nginx reverse-proxies API paths to the in-pod API container (see
  [`ui/nginx-default.conf`](../ui/nginx-default.conf)).
