# Kubeseal-Webgui Helm Chart

* Installs the python based webapp for kubeseal-webgui

## TL;DR
```console
helm repo add kubesealwebgui https://jaydee94.github.io/kubeseal-webgui/
helm repo update
helm install kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename>

# with ingress and autofetch certificate
helm install kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename> --set ingress.enabled=true --set api.url="http://kubeseal-webgui.example.com" --set sealedSecrets.autoFetchCert=true
```

## Uninstalling the Chart

To uninstall/delete the my-release deployment:

```console
helm uninstall kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename>
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Configuration

| Parameter                                 | Description                                       | Default                       |
| ----------------------------------------- | ------------------------------------------------- | ----------------------------- |
| `replicaCount`                            | Number of nodes                                   | `1`                           |
| `annotations`                             | Optional annotations for the pods                 | `{}`                          |
| `api.image.repository`                    | Image-Repository and name of the api image.       | `kubesealwebgui/api`          |
| `api.image.tag`                           | Image Tag of the api image.                       | `4.2.5`                       |
| `api.environment`                         | Additional env variables for the api image.       | `{}`                          |
| `api.loglevel`                            | Loglevel for the api image.                       | `INFO`                        |
| `ui.image.repository`                     | Image-Repository and name of the ui image.        | `kubesealwebgui/ui`           |
| `ui.image.tag`                            | Image Tag of the ui image.                        | `4.2.5`                       |
| `image.pullPolicy`                        | Image Pull Policy                                 | `Always`                      |
| `nameOverride`                            | Name-Override for the objects                     | `""`                          |
| `fullnameOverride`                        | Fullname-Override for the objects                 | `""`                          |
| `customServiceAccountName`                | Optionallyn define your own serviceaccount to use | `true`                        |
| `tolerations`                             | Add tolerations to the deployment.                | `[]`                          |
| `affinity`                                | Add affinity rules to the deployment.             | `{}`                          |
| `nodeSelector`                            | Add a nodeSelector to the deployment.             | `{}`                          |
| `displayName`                             | Optional display name for the kubeseal instance   | `""`                          |
| `resources.limits.cpu`                    | Limits CPU                                        | `100m`                        |
| `resources.limits.memory`                 | Limits memory                                     | `256Mi`                       |
| `resources.requests.cpu`                  | Requests CPU                                      | `20m`                         |
| `resources.requests.memory`               | Requests memory                                   | `20m`                         |
| `ingress.enabled`                         | Enable an ingress route                           | `false`                       |
| `ingress.annotations`                     | Additional annotations for the ingress object.    | `{}`                          |
| `ingress.ingressClassName`                | Additional ingressClassName.                      | `""`                          |
| `ingress.hostname`                        | The hostname for the ingress route                | `kubeseal-webgui.example.com` |
| `ingress.tls.enabled`                     | Enable TLS for the ingress route                  | `false`                       |
| `ingress.tls.secretName`                  | The secret name for private and public key        | `""`                          |
| `route.enabled`                           | Deploy OpenShift route                            | `false`                       |
| `route.hostname`                          | Set Hostname of the route                         | `""`                          |
| `route.tls.enabled`                       | Enable/Disable TLS for OpenShift Route            | `true`                        |
| `route.tls.termination`                   | TLS Termination of the route                      | `""`                          |
| `route.tls.insecureEdgeTerminationPolicy` | TLS insecureEdgeTerminationPolicy of the route    | `""`                          |
| `sealedSecrets.autoFetchCert`             | Load the cert from the Controller on start        | `false`                       |
| `sealedSecrets.controllerName`            | Deployment name of the Controller                 | `sealed-secrets-controller`   |
| `sealedSecrets.controllerNamespace`       | Namespace the Controller resides in               | `kube-system`                 |
| `sealedSecrets.cert`                      | Public-Key of your SealedSecrets controller       | `""`                          |
| `api.environment`                         | Additional API environment variables              | `{}`                          |
