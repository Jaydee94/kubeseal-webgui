# Kubeseal-Webgui Helm Chart

* Installs the python based webapp for kubeseal-webgui

## TL;DR
```console
helm repo add kubesealwebgui https://jaydee94.github.io/kubeseal-webgui/
helm repo update
helm install kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename>

# with ingress and autofetch certificate
helm install kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename> --set ingress.enabled=true --set publicUrl="http://kubeseal-webgui.example.com" --set sealedSecrets.autoFetchCert=true
```

## Uninstalling the Chart

To uninstall/delete the my-release deployment:

```console
helm uninstall kubeseal-webgui kubesealwebgui/kubeseal-webgui --namespace <namespacename>
```
The command removes all the Kubernetes components associated with the chart and deletes the release.

## Configuring multiple environments in one kubeseal-webgui ui

With version `>=5.0.0` it is possible to configure multiple environments/clusters to be displayed in one ui component.

* Deploy one ui component and the api component of kubeseal-webgui in your desired cluster by setting `ui.enabled` and `api.enabled` to `true`.
* For every cluster that should be displayed in the same ui you have deploy the api component and expose the api with an ingress or route object.
  * `ui.enabled` to `false`
  * `api.enabled` to `true`
  * `api.ingress.enabled` or `api.route.enabled` to `true`
* For security reasons (CORS) the api components need to know the host from which the api gets called. So the parameter `publicUrl` has to be set to the HTTP Endpoint of the ui component.
* The ui component needs to know the kubeseal-webgui APIs of each cluster you want to add in the ui.
  * The API endpoints have to be configured with the parameter `ui.environments`.

### Example for configuring multiple environments

#### Cluster Foo (provides the ui)

```yaml
publicUrl: "http://kubeseal-webgui-ui.foo.example.com"
api:
  enabled: true
  ...
  ingress:
    enabled: false
  ...
...
ui:
  enabled: true
  ...
  environments:
    cluster-foo: "http://localhost:5000"
    cluster-bar: "http://kubeseal-webgui-api.bar.example.com"
  ...
  ingress:
    enabled: true
    hostname: "kubeseal-webgui-ui.foo.example.com"
  ...
...
```

#### Cluster Bar (should be displayed in the ui of Cluster Foo)

```yaml
publicUrl: "http://kubeseal-webgui-ui.foo.example.com"
api:
  enabled: true
  ...
  ingress:
    enabled: true
    hostname: "kubeseal-webgui-api.bar.example.com"
  ...
...
ui:
  enabled: false
...
```



## Configuration

| Parameter                                     | Description                                          | Default                       |
| --------------------------------------------- | ---------------------------------------------------- | ----------------------------- |
| `replicaCount`                                | Number of nodes                                      | `1`                           |
| `annotations`                                 | Optional annotations for the pods                    | `{}`                          |
| `publicUrl`                                   | The HTTP Endpoint for accessing the ui.              | `http://localhost:8080`       |
| `api.enabled`                                 | Enable-Disable api component                         | `true`                        |
| `api.image.repository`                        | Image-Repository and name of the api image.          | `kubesealwebgui/api`          |
| `api.image.tag`                               | Image Tag of the api image.                          | `5.0.0`                       |
| `api.env`                                     | Additional env variables for the api image.          | `{}`                          |
| `api.ingress.enabled`                         | Enable an ingress route for the api                  | `false`                       |
| `api.ingress.annotations`                     | Additional annotations for the ingress object.       | `{}`                          |
| `api.ingress.ingressClassName`                | Additional ingressClassName.                         | `""`                          |
| `api.ingress.hostname`                        | The hostname for the ingress route                   | `kubeseal-webgui.example.com` |
| `api.ingress.tls.enabled`                     | Enable TLS for the ingress route                     | `false`                       |
| `api.ingress.tls.secretName`                  | The secret name for private and public key           | `""`                          |
| `api.route.enabled`                           | Deploy OpenShift route for the api                   | `false`                       |
| `api.route.hostname`                          | Set Hostname of the route                            | `""`                          |
| `api.route.tls.enabled`                       | Enable/Disable TLS for OpenShift Route               | `true`                        |
| `api.route.tls.termination`                   | TLS Termination of the route                         | `""`                          |
| `api.route.tls.insecureEdgeTerminationPolicy` | TLS insecureEdgeTerminationPolicy of the route       | `""`                          |
| `api.loglevel`                                | Loglevel for the api image.                          | `INFO`                        |
| `ui.enabled`                                  | Enable-Disable ui component.                         | `true`                        |
| `ui.image.repository`                         | Image-Repository and name of the ui image.           | `kubesealwebgui/ui`           |
| `ui.image.tag`                                | Image Tag of the ui image.                           | `5.0.0`                       |
| `ui.ingress.enabled`                          | Enable an ingress route for the ui                   | `false`                       |
| `ui.ingress.annotations`                      | Additional annotations for the ingress object.       | `{}`                          |
| `ui.ingress.ingressClassName`                 | Additional ingressClassName.                         | `""`                          |
| `ui.ingress.hostname`                         | The hostname for the ingress route                   | `kubeseal-webgui.example.com` |
| `ui.ingress.tls.enabled`                      | Enable TLS for the ingress route                     | `false`                       |
| `ui.ingress.tls.secretName`                   | The secret name for private and public key           | `""`                          |
| `ui.route.enabled`                            | Deploy OpenShift route for the ui                    | `false`                       |
| `ui.route.hostname`                           | Set Hostname of the route                            | `""`                          |
| `ui.route.tls.enabled`                        | Enable/Disable TLS for OpenShift Route               | `true`                        |
| `ui.route.tls.termination`                    | TLS Termination of the route                         | `""`                          |
| `ui.route.tls.insecureEdgeTerminationPolicy`  | TLS insecureEdgeTerminationPolicy of the route       | `""`                          |
| `ui.environments`                             | The environments that should be available in the ui. | `{}`                          |
| `image.pullPolicy`                            | Image Pull Policy                                    | `Always`                      |
| `nameOverride`                                | Name-Override for the objects                        | `""`                          |
| `fullnameOverride`                            | Fullname-Override for the objects                    | `""`                          |
| `customServiceAccountName`                    | Optionallyn define your own serviceaccount to use    | `true`                        |
| `tolerations`                                 | Add tolerations to the deployment.                   | `[]`                          |
| `affinity`                                    | Add affinity rules to the deployment.                | `{}`                          |
| `nodeSelector`                                | Add a nodeSelector to the deployment.                | `{}`                          |
| `displayName`                                 | Optional display name for the kubeseal instance      | `""`                          |
| `resources.limits.cpu`                        | Limits CPU                                           | `100m`                        |
| `resources.limits.memory`                     | Limits memory                                        | `256Mi`                       |
| `resources.requests.cpu`                      | Requests CPU                                         | `20m`                         |
| `resources.requests.memory`                   | Requests memory                                      | `20m`                         |
| `sealedSecrets.autoFetchCert`                 | Load the cert from the Controller on start           | `false`                       |
| `sealedSecrets.controllerName`                | Deployment name of the Controller                    | `sealed-secrets-controller`   |
| `sealedSecrets.controllerNamespace`           | Namespace the Controller resides in                  | `kube-system`                 |
| `sealedSecrets.cert`                          | Public-Key of your SealedSecrets controller          | `""`                          |
