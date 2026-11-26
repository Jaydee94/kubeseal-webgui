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
| `commonLabels` | Additional labels to add to every chart-managed object. Built-in chart labels (`app`, `chart`, `release`, `heritage`) are always preserved. | `{}` |
| `annotations` | Additional pod annotations. | `{}` |
| `api.image.repository` | API image repository. | `ghcr.io/jaydee94/kubeseal-webgui/api` |
| `api.image.tag` | API image tag. | Matches chart `appVersion` (see [Chart.yaml](../chart/kubeseal-webgui/Chart.yaml)). |
| `ui.image.repository` | UI image repository. | `ghcr.io/jaydee94/kubeseal-webgui/ui` |
| `ui.image.tag` | UI image tag. | Matches chart `appVersion` (see [Chart.yaml](../chart/kubeseal-webgui/Chart.yaml)). |
| `ui.ipv6.enabled` | Let the UI's nginx listen on IPv6 in addition to IPv4. Set to `false` on nodes with IPv6 disabled in the kernel, where nginx cannot start otherwise (see [troubleshooting](troubleshooting.md#ui-container-does-not-start-address-family-not-supported)). Needs a UI image newer than 4.17.0. | `true` |
| `image.pullPolicy` | Image pull policy. | `Always` |
| `imagePullSecrets` | Image pull secrets for private registries. | `[]` |
| `nameOverride` | Override the chart name component of object names. | `""` |
| `fullnameOverride` | Override the full release name. | `""` |
| `displayName` | Optional display name for this kubeseal-webgui instance. | `""` |

### Service account and RBAC

| Parameter | Description | Default |
|---|---|---|
| `customServiceAccountName` | Use an existing `ServiceAccount` instead of the one shipped with the chart. The account must be able to list namespaces (unless `enableNamespaceListing=false`). Leave empty to use the bundled `ServiceAccount` and `ClusterRole`. | `""` |
| `enableNamespaceListing` | Let the UI offer the namespaces of the cluster to pick from. Set to `false` where the API may not list namespaces (no cluster-wide RBAC, e.g. as an OpenShift project admin): the namespace is then typed in, nothing requests `/namespaces`, and the chart drops the `namespaces` rule from its `ClusterRole`. | `true` |

The bundled `ClusterRole`
([`clusterrole.yaml`](../chart/kubeseal-webgui/templates/clusterrole.yaml))
grants `list` on `namespaces` and `get`/`list` on
`sealedsecrets.bitnami.com`.

With `enableNamespaceListing=false` it only grants the `sealedsecrets`
rule, and only if `enableExistingSealedSecretLoading=true`; with both off
the chart creates no `ClusterRole` or `ClusterRoleBinding` and installs
without cluster-wide RBAC. To import existing SealedSecrets without
cluster-wide RBAC, use `customServiceAccountName` and grant `get`/`list` on
`sealedsecrets.bitnami.com` with a `Role` and `RoleBinding` in each target
namespace yourself: the API only reads the namespace that was entered.

### Networking

#### Ingress

| Parameter | Description | Default |
|---|---|---|
| `ingress.enabled` | Create an `Ingress` object. | `false` |
| `ingress.annotations` | Additional annotations on the `Ingress`. | `{}` |
| `ingress.ingressClassName` | `ingressClassName` to set on the `Ingress`. | `""` |
| `ingress.hostname` | Hostname for the ingress route. | `kubeseal-webgui.example.com` |
| `ingress.path` | Path the UI is served under, e.g. `/kubeseal-webgui` (see [installation.md](installation.md#under-a-path-prefix)). Include it in `api.url`. | `/` |
| `ingress.tls.enabled` | Enable TLS on the ingress route. | `false` |
| `ingress.tls.secretName` | Name of the TLS secret (must exist in the release namespace). | `""` |

#### OpenShift Route

| Parameter | Description | Default |
|---|---|---|
| `route.enabled` | Create an OpenShift `Route`. | `false` |
| `route.hostname` | Hostname of the route. Empty lets OpenShift assign one. | `""` |
| `route.path` | Path the UI is served under, see `ingress.path`. | `/` |
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
| `sealedSecrets.certs` | Several clusters, each with the certificate of its own controller, see [Several clusters](#several-clusters). | `[]` |
| `enableExistingSealedSecretLoading` | UI feature flag: allow importing keys from existing `SealedSecret` objects in a namespace. | `false` |
| `defaultScope` | The scope the UI starts with and returns to on "Clear": `strict`, `namespace-wide` or `cluster-wide`. Users can still pick another scope per secret. Any other value fails the chart render. With `cluster-wide`, secrets sealed without looking at the scope can be unsealed in any namespace. | `strict` |

#### Several clusters

A value sealed with the certificate of one cluster cannot be unsealed in
another. To seal for several clusters from one installation, list them in
`sealedSecrets.certs`:

```yaml
sealedSecrets:
  autoFetchCert: true
  certs:
    - name: acc
      inCluster: true        # the cluster this release runs in; certificate auto-fetched
    - name: prod
      cert: |
        -----BEGIN CERTIFICATE-----
        ...
```

- `name`: lower case letters, digits and `-`, unique. The first entry is
  preselected in the UI, and used by API requests that name no cluster.
- `cert`: the PEM certificate (`kubeseal --fetch-cert` in that cluster).
  Required, except for an `inCluster` entry with `autoFetchCert=true`.
- `inCluster`: at most one entry. Only for this cluster can the UI list
  namespaces and load existing SealedSecrets (they are read through the API's
  own service account). For every other cluster the namespace is typed in.
- Leave `certs` empty to keep a single cluster using `sealedSecrets.cert`.

The certificates of other clusters are static: replace them with a
`helm upgrade` when a controller's certificate changes. The UI shows the
SHA-256 fingerprint of the selected cluster's certificate, to compare with
the one of the cluster. A certificate of the wrong cluster seals without an
error and fails only when the secret is deployed.

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
| `extraVolumes` | Additional volumes of the pod (Kubernetes `volumes` entries), mounted with the two values below. | `[]` |
| `api.extraVolumeMounts` | Additional `volumeMounts` of the `api` container. | `[]` |
| `ui.extraVolumeMounts` | Additional `volumeMounts` of the `ui` container, e.g. an own nginx server block over `/etc/nginx/conf.d/default.conf` (see [below](#own-files-in-the-containers)). | `[]` |
| `api.url` | Public URL of the API as seen by the browser. Rendered into the UI's `config.json` ConfigMap. | `http://localhost:8080` |
| `api.loglevel` | Log level for the API container (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | `INFO` |
| `api.logformat` | Log output format of the API container: `text` or `json` (one JSON object per line, for log aggregators). | `text` |
| `api.environment` | Additional environment variables for the API container as a map. | `{}` |

### Own files in the containers

`extraVolumes` together with `api.extraVolumeMounts` / `ui.extraVolumeMounts`
mount files the chart does not provide, for example a custom CA bundle or an
own nginx server block for the UI:

```yaml
extraVolumes:
  - name: nginx-server-block
    configMap:
      name: my-nginx-server-block   # with a key "default.conf"
ui:
  extraVolumeMounts:
    - name: nginx-server-block
      mountPath: /etc/nginx/conf.d/default.conf
      subPath: default.conf
      readOnly: true
```

- A replaced server block is not updated with the image. Start from
  [`ui/nginx-default.conf`](../ui/nginx-default.conf) of the image version
  in use and check it again on every upgrade: the API routes and the path
  prefix handling live in it.
- Do not reuse a `mountPath` the chart already mounts (`/tmp`, the
  certificate, `logging_config.yaml`, `config.json`): Kubernetes rejects a
  pod with two mounts at the same path. Volume names must not clash with the
  chart's own (`sealed-secret-configmap`, `sealed-secrets-certs`, `tmp`).
- The root filesystem is read-only (`containerSecurityContext`); mount
  writable paths as `emptyDir`.
- Files mounted with `subPath` are not updated in a running pod when the
  ConfigMap changes; restart the deployment.

### Security context

| Parameter | Description | Default |
|---|---|---|
| `securityContext` | Pod-level `securityContext`, applied to the whole pod (see [`deployment.yaml`](../chart/kubeseal-webgui/templates/deployment.yaml)). | `enabled: true`, `runAsNonRoot: true`, `seccompProfile.type: RuntimeDefault` |
| `containerSecurityContext` | Container-level `securityContext`, applied identically to both the `api` and `ui` containers. | `enabled: true`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]` |

Both images run as a fixed, non-root numeric UID baked into the image
itself (both Chainguard base images default to the nonroot uid 65532), so
there is no need to set
`securityContext.runAsUser` — the chart's default `securityContext` is
compatible with both images out of the box.

`enabled` is a chart-only switch, not a real Kubernetes `securityContext`
field — the chart strips it before rendering. Set
`securityContext.enabled=false` and/or `containerSecurityContext.enabled=false`
to render no `securityContext` block at all at that level, letting the
platform's own admission controller fully own it instead — most relevant on
**OpenShift**, whose default `restricted`/`restricted-v2` SCC assigns its own
`runAsUser`/`fsGroup`/`seLinuxOptions` from a namespace-scoped range and
already enforces non-root execution; a chart-supplied `securityContext` can
be redundant with, or in some configurations rejected by, that assignment.
The two flags are independent: disable either or both as your platform
requires.

## API environment variables

These are read directly by the API process and can be set via
`api.environment` in the Helm values. Source:
[`api/kubeseal_webgui_api/app_config.py`](../api/kubeseal_webgui_api/app_config.py).

| Variable | Description | Default |
|---|---|---|
| `KUBESEAL_BINARY` | Absolute path to the `kubeseal` executable inside the container. | `/kubeseal-webgui/bin/kubeseal` (set in `Dockerfile.api`) |
| `KUBESEAL_CERT` | Path to the controller's public certificate. | `/kubeseal-webgui/cert/kubeseal-cert.pem` |
| `KUBESEAL_CLUSTERS_FILE` | Path of a JSON file listing several clusters, each `{"name": ..., "cert": <path>, "inCluster": <bool>}` (`cert` can be left out for the `inCluster` entry, which then uses `KUBESEAL_CERT`). The first entry is the default. Set by the chart for `sealedSecrets.certs`. A broken file, or a missing certificate in it, stops the API at startup. Empty: one cluster named `default`, sealed with `KUBESEAL_CERT`. | empty |
| `KUBESEAL_AUTOFETCH` | Set to `true` to fetch the certificate from the controller on startup. Set by the chart when `sealedSecrets.autoFetchCert=true`. A boolean: `true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off` in any case; any other value stops the API at startup. | `false` |
| `KUBESEAL_CONTROLLER_NAME` | Deployment name of the Sealed Secrets controller (used when auto-fetching). | `sealed-secrets-controller` |
| `KUBESEAL_CONTROLLER_NAMESPACE` | Namespace of the Sealed Secrets controller (used when auto-fetching). | `sealed-secrets` in the API code, overridden to match `sealedSecrets.controllerNamespace` by the chart. |
| `ORIGIN_URL` | The one origin that may call the API from a browser page served elsewhere (CORS). Only scheme, host and port are used. Set by the chart to `api.url`. Not needed when UI and API share an origin, as behind the chart's ingress; a value that is not an absolute URL allows no other origin. | `http://localhost:8080` (the UI dev server) |
| `MOCK_ENABLED` | Replace the Kubernetes client and `kubeseal` invocations with in-memory mocks. Useful for local development without a cluster; no `kubeseal` binary is needed. A boolean like `KUBESEAL_AUTOFETCH`. | `false` |

## UI configuration

The UI is a static SPA. The chart renders `api.url` into a `config.json`
ConfigMap that is mounted next to the bundled HTML, so the browser knows
where to find the API.

You only need to set one value:

- `api.url`: the public URL of the API as the browser sees it. With the
  bundled chart this is usually the same URL as the UI itself, because the
  UI's nginx reverse-proxies API paths to the in-pod API container (see
  [`ui/nginx-default.conf`](../ui/nginx-default.conf)).
  Under a path prefix it includes the path. An empty value makes the UI call
  the API relative to its own address.
