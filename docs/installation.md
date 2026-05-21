# Installation

This guide walks through deploying kubeseal-webgui to a Kubernetes cluster using
the bundled Helm chart.

For local development on your laptop, see [development.md](development.md).
For a full list of tunable values, see [configuration.md](configuration.md).

## Prerequisites

- A Kubernetes cluster (1.25 or newer).
- The [Bitnami Sealed Secrets controller](https://github.com/bitnami-labs/sealed-secrets)
  already installed in the cluster. kubeseal-webgui does not install the
  controller itself; it only encrypts secrets against the controller's public
  certificate.
- [Helm 3.8 or newer](https://helm.sh/docs/intro/install/) (required for the OCI
  installer).
- `kubectl` configured for the target cluster.
- An ingress controller (for `Ingress`) or OpenShift (for `Route`) if you want
  to expose the UI outside the cluster.

## Install with Helm (OCI)

The chart is published as an OCI artifact to the GitHub Container Registry:

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui \
  --create-namespace
```

This deploys both containers (UI + API) into a single pod behind a `ClusterIP`
service. To reach the UI from outside the cluster, enable an ingress route or
an OpenShift route as shown below.

### With an Ingress

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui --create-namespace \
  --set ingress.enabled=true \
  --set ingress.hostname=kubeseal-webgui.example.com \
  --set api.url=https://kubeseal-webgui.example.com
```

The `api.url` value is baked into the UI's `config.json` ConfigMap and tells
the browser where to reach the API. It must match the public URL the user types
into their browser.

To enable TLS, set `ingress.tls.enabled=true` and point `ingress.tls.secretName`
at a TLS secret that already exists in the release namespace.

### On OpenShift (Route)

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui --create-namespace \
  --set route.enabled=true \
  --set api.url=https://kubeseal-webgui.apps.example.com
```

Leave `route.hostname` empty to let OpenShift assign a hostname from the
default apps subdomain.

## Sealed-Secrets certificate

The API needs the controller's public certificate to encrypt secrets. There
are two ways to provide it.

### Option A: Auto-fetch from the controller

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui --create-namespace \
  --set sealedSecrets.autoFetchCert=true \
  --set sealedSecrets.controllerName=sealed-secrets-controller \
  --set sealedSecrets.controllerNamespace=kube-system
```

The API container fetches the certificate from the controller on startup. The
chart's `ClusterRole` already grants the permissions needed to talk to the
controller. Make sure `controllerName` and `controllerNamespace` match the
actual deployment of your Sealed Secrets controller.

### Option B: Provide the certificate manually

If you cannot grant the cluster-wide RBAC required by auto-fetch, fetch the
certificate yourself and pass it inline:

```bash
kubeseal --fetch-cert \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  > kubeseal-cert.pem

helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui --create-namespace \
  --set-file sealedSecrets.cert=kubeseal-cert.pem
```

The chart renders the certificate into a Secret mounted at
`/kubeseal-webgui/cert/kubeseal-cert.pem` inside the API container.

## Verifying the install

```bash
kubectl get pods -n kubeseal-webgui
```

Once the pod is `Ready`, port-forward and hit the API health endpoint:

```bash
kubectl port-forward -n kubeseal-webgui svc/kubeseal-webgui 8080:8080
curl http://localhost:8080/
# {"status":"Kubeseal-WebGui API"}
```

If you enabled an ingress or route, open the configured hostname in a browser.

## Uninstalling

```bash
helm uninstall kubeseal-webgui --namespace kubeseal-webgui
```

This removes all Kubernetes objects created by the chart. The namespace is
not deleted automatically.
