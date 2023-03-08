# API of kubeseal-webgui

This backend is used to encrypt secrets with the kubeseal binary.

## External dependencies

The application acts mostly as data broker. The actual information
comes from external service such as the Kubernetes API or by
invoking executables.

### `kubeseal`

Secret management is done via `kubeseal`. The application must be
able to invoke this binary. The lookup location can be customized
via the *KUBESEAL_BINARY* environment variable.

### Kubernetes API

Additional information, such as the available namespaces, is fetched
from the Kubernetes API. Currently the application requires to be
ran inside a Kubernetes cluster itself, as it connects to the interal
API for data retrieval.

Namespaces are fetched via the namespace [list endpoint][].
If the cluster role in use is not allowed to use this endpoint,
the application can also determine the list of available namespaces
by fetching a list of alternative resources and parse their metadata
for the required information. Internally it uses the
`list_K8S_NAMESPACE_RESOURCE_for_all_namespaces` methods from the
Kubernetes Python Client [core API][] object, where *K8S_NAMESPACE_RESOURCE*
is replaced with the value from the environment variable of the same name.
The resulting list is limited to all namespaces which are accessible and
have at least one instance of the given resource type.

[list endpoint]: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.22/#list-namespace-v1-core
[core API]: https://github.com/kubernetes-client/python/blob/master/kubernetes/README.md#documentation-for-api-endpoints

