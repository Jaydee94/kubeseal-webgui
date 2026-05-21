# kubeseal-webgui UI

Vue 3 + [Vuetify 4](https://vuetifyjs.com/) single-page application, built
with [Vite](https://vite.dev/) and served by nginx in production.

The UI reads `config.json` at startup to discover the API URL, so the same
container image can be deployed to any environment without rebuilding.

## More documentation

- Architecture and reverse-proxy layout: [../docs/architecture.md](../docs/architecture.md)
- Running and testing locally: [../docs/development.md#ui-vue-3--vite](../docs/development.md#ui-vue-3--vite)
- Container build: [../Dockerfile.ui](../Dockerfile.ui)
