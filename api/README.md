# kubeseal-webgui API

FastAPI backend that wraps the [`kubeseal`](https://github.com/bitnami-labs/sealed-secrets)
binary. It exposes the encryption operation, plus a couple of helpers for
listing namespaces and existing `SealedSecret` objects, as a small HTTP API.

OpenAPI documentation is served at `/docs` when the API is running.

## More documentation

- Architecture and request flow: [../docs/architecture.md](../docs/architecture.md)
- Running and testing locally: [../docs/development.md#api-python--fastapi](../docs/development.md#api-python--fastapi)
- Environment variables: [../docs/configuration.md#api-environment-variables](../docs/configuration.md#api-environment-variables)
- Container build: [../Dockerfile.api](../Dockerfile.api)
