# kubeseal-webgui Helm chart

Helm chart for deploying [kubeseal-webgui](https://github.com/Jaydee94/kubeseal-webgui)
to a Kubernetes cluster.

For a step-by-step install (with ingress, OpenShift route, and certificate
options), see [docs/installation.md](../../docs/installation.md).
For the full Helm values reference, see
[docs/configuration.md](../../docs/configuration.md#helm-values).

## TL;DR

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui \
  --create-namespace
```

With an ingress and auto-fetched certificate:

```bash
helm install kubeseal-webgui \
  oci://ghcr.io/jaydee94/kubeseal-webgui/charts/kubeseal-webgui \
  --namespace kubeseal-webgui --create-namespace \
  --set ingress.enabled=true \
  --set ingress.hostname=kubeseal-webgui.example.com \
  --set api.url=https://kubeseal-webgui.example.com \
  --set sealedSecrets.autoFetchCert=true
```

## Uninstalling

```bash
helm uninstall kubeseal-webgui --namespace kubeseal-webgui
```

This removes every Kubernetes object created by the chart. The namespace is
not deleted automatically.

## More documentation

- [Installation guide](../../docs/installation.md)
- [Configuration reference](../../docs/configuration.md)
- [Architecture](../../docs/architecture.md)
- [Troubleshooting](../../docs/troubleshooting.md)
