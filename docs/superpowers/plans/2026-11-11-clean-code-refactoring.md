# Clean Code Refactoring (API + UI) Implementation Plan

**Goal:** Remove the structural clean-code problems found in a full read of the
Python API and the Vue UI, without changing what the application does for its
users or its API clients.

**Scope:** `api/` (FastAPI) and `ui/` (Vue 3 + Vuetify). Helm chart,
Dockerfiles and nginx config are out of scope except where a task names them.

**Spec:** No separate spec. Every finding below was verified against the code
at commit `b7053ef`, and the baselines in "Verified baseline" were measured in
that state.

## Global constraints

- **No behaviour change unless a task says so.** The HTTP contract
  (`GET /`, `/config`, `/namespaces`, `/sealed-secrets/{namespace}`,
  `POST /secrets`, JSON field names including the `secret` alias and the
  camelCase `kubesealVersion`), the env variable names and the generated
  SealedSecret YAML text must stay exactly as they are.
- **Do not rename** `RequestIdMiddleware`, `RequestIdFilter`,
  `HealthCheckAccessFilter`, `JsonFormatter` or move them out of
  `kubeseal_webgui_api.logging_utils`: they are referenced by name from
  `api/config/logging_config.yaml` and the chart's copy, and users ship their
  own logging configs.
- **Never log secret values, file contents or request bodies**, in either
  code base. Keep the existing comments that explain this.
- One commit per task, conventional-commit style (`refactor(api): ...`,
  `test(ui): ...`). Run the task's verification before committing. If a
  verification fails and cannot be fixed within the task's scope, revert the
  task and record why in "Execution notes" at the bottom of this file.
- Do not add TypeScript, Pinia, a router or any other new runtime dependency.
  The only new dev dependency allowed is `vitest` (Task 9).

## Verified baseline

Measured before any change; every task must leave these at least as good.

| Check | Command (from repo root) | Baseline |
|---|---|---|
| API unit tests | `cd api && KUBESEAL_BINARY=/bin/true poetry run pytest -q -m "not container and not cluster"` | 64 passed, 6 deselected |
| API tests as documented | `cd api && poetry run pytest` | **collection error** (4 modules) |
| API import in mock mode | `cd api && MOCK_ENABLED=true poetry run python -c "import kubeseal_webgui_api.app"` | **RuntimeError** |
| ruff | `cd api && poetry run ruff check .` | 39 findings |
| mypy | `cd api && poetry run mypy kubeseal_webgui_api` | 3 errors |
| black / isort | `poetry run black --check .` / `poetry run isort --check .` | 2 / 2 files fail |
| ESLint | `cd ui && npx eslint .` | clean |
| Prettier | `cd ui && npx prettier --check src/` | all 18 files fail |
| UI build | `cd ui && npx vite build` | ok; JS 798 kB, CSS 886 kB |
| UI E2E | dev server on :8080, then `cd ui && pytest tests -q` | 6 passed |

Notes on running the E2E tests in a sandbox where the Python Playwright
version does not match the pre-installed browser: do not run
`playwright install`. Point `PLAYWRIGHT_BROWSERS_PATH` at a scratch directory
containing symlinks named after the revision Playwright asks for
(`chromium_headless_shell-<rev>`, `chromium-<rev>`) that point at the
installed `/opt/pw-browsers/...` directories. Use the API's poetry venv
(`poetry -C api env info -p`) as the interpreter; it has `playwright` and
`pytest` installed.

---

## Phase 1 — Safety net first

### Task 1: Make the UI E2E tests assert the sealing flow

**Finding.** `click_encrypt_button` in `ui/tests/test_ui.py` tries to replace
`fetchEncodedSecrets` on the root component's proxy. The root component is
`App`, not `Secrets`, so nothing is replaced: the real `POST /secrets` is sent,
fails with HTTP 502 (no API behind the dev server), the UI shows an error
snackbar, and the test still passes. The result view (the generated YAML, the
per-key cards, Clear / Edit) is not covered by any test. Every test also
repeats the same browser start-up code and writes temp files into the working
directory.

**Do.**
- Replace the proxy patching with `page.route("**/secrets", ...)` that fulfils
  the POST with a JSON list such as
  `[{"key": "my-secret-key", "value": "AgSealedValue"}]`, and assert on the
  request body (JSON keys `secret`, `namespace`, `scope`, `secrets[0].key`,
  and base64 `value` or `file`).
- After clicking Encrypt, assert the result view: the exact text of
  `#sealed-secret-result` for the strict scope, and one more test for
  `namespace-wide` without a secret name (pins the
  `# no secret name given` placeholder and the annotation line). These exact
  strings are the regression guard for Task 10.
- Add a test for a failing seal (route fulfils with 500 and a `detail`): the
  form stays visible and the snackbar shows the detail.
- Add a test for Clear and for Edit Secrets on the result view.
- Use a shared fixture for browser/page (pytest-playwright's `page` fixture
  with a `base_url`, or a local fixture) and `tmp_path` for the files.

**Verify.** E2E suite green; temporarily break the YAML template locally to
confirm the new assertion fails, then restore.

---

## Phase 2 — Python API

### Task 2: Remove import-time side effects from `app_config.py`

**Findings.**
- `settings = AppSettings(kubeseal_version=get_kubeseal_version())` runs the
  kubeseal binary while the module is imported. Consequences, all measured:
  `poetry run pytest` (as documented in `docs/development.md` and
  `CONTRIBUTING.md`) cannot even collect the tests, and
  `MOCK_ENABLED=true uvicorn ...` (the documented no-cluster dev command)
  crashes unless `KUBESEAL_BINARY` also points at something that prints a
  version.
- Configuration is read twice with different rules: module globals `binary`,
  `mock`, `autofetch`, `kubeseal_cert` are parsed by hand from `os.environ`,
  and `AppSettings` declares the same values again. `KUBESEAL_CERT` has two
  different defaults (`/kubeseal-webgui/cert/kubeseal-cert.pem` for writing
  the fetched cert, `/dev/null` for sealing).
- `autofetch` is a string compared with `"false"`, so `KUBESEAL_AUTOFETCH=False`
  or `0` turns auto-fetch **on**.
- `fetch_sealed_secrets_cert` reads two more env variables inline.

**Do.**
- Make `AppSettings` the single source: fields `kubeseal_binary`,
  `kubeseal_cert`, `kubeseal_autofetch: bool`, `mock_enabled: bool`,
  `mock_namespace_count`, `kubeseal_controller_namespace`,
  `kubeseal_controller_name`, populated by pydantic-settings from the existing
  env names (`KUBESEAL_BINARY`, `KUBESEAL_CERT`, `KUBESEAL_AUTOFETCH`,
  `MOCK_ENABLED`, `KUBESEAL_CONTROLLER_NAMESPACE`, `KUBESEAL_CONTROLLER_NAME`).
  One default for the cert path: `/kubeseal-webgui/cert/kubeseal-cert.pem`
  (the documented one). Keep the default binary `/bin/false`.
- `kubeseal_version` is no longer a constructor argument. Resolve it once at
  application start-up (in `lifespan`) and cache it; in mock mode do not run
  the binary and report the existing mock version `0.1.0`. A real deployment
  with a broken binary must still fail at start-up with the same error
  message, not on the first request.
- Delete the module-level `binary` / `mock` / `autofetch` / `kubeseal_cert`
  globals and update `app.py`, the routers and the tests that patch
  `settings.*`.
- `routers/config.py`: drop the `try/except RuntimeError` around a constructor
  that cannot raise it.

**Behaviour changes (intended, document in the commit message):**
`KUBESEAL_AUTOFETCH` accepts the usual boolean spellings; mock mode no longer
needs a binary; importing the package has no side effects.

**Verify.** `poetry run pytest -m "not container and not cluster"` passes
**without** `KUBESEAL_BINARY`; the mock-mode import command from the baseline
table succeeds; `GET /config` in mock mode still returns
`{"kubesealVersion": "0.1.0"}`; add tests for the settings parsing and for
"start-up fails when the binary is unusable and mock mode is off".

### Task 3: Simplify the sealing pipeline in `routers/kubeseal.py`

**Findings.**
- `encrypt_value_or_file` takes 8 parameters and has two `@overload`s whose
  only purpose is to switch `Popen` between text and bytes mode; the two
  branches after `Popen` do the same thing twice.
- `run_kubeseal_command` duplicates the call for value and file.
- Names mislead: `cleartext_secret_tuple` is a `Secret` model,
  `kubeseal_command_cmd`, `exec_kubeseal_command`, `verify`,
  `list_of_non_dict_inputs` (checks for `Secret`, message says "dicts").
- The "not a list of dicts" check in `run_kubeseal` is unreachable through the
  API (pydantic already validated `list[Secret]`).
- `Secret.value_or_file_set` raises `AssertionError` and mixes truthiness with
  `is None`: `{"value": "", "file": "<data>"}` passes validation and then
  seals the empty string, silently ignoring the file.
- `binary` and `cert` are threaded through three functions although they
  always come from `settings`.

**Do.**
- Always hand bytes to kubeseal: decode the base64 payload to `bytes` for both
  value and file (keep the UTF-8 validity check for `value`, because the
  current code rejects non-UTF-8 values with a 400 and
  `loggable_reason` depends on `UnicodeError`), then one
  `subprocess.run(command, input=payload, capture_output=True, check=False)`.
  Remove the overloads and the `encoding` parameter.
- Collapse to small functions with honest names, e.g. `seal_secrets` →
  `seal_entry` → `build_kubeseal_command`; keep `valid_k8s_name`,
  `decode_base64_*` behaviour and the error message formats
  (`Error in run_kubeseal (exit code N): ...`, `Could not find kubeseal
  binary`) because tests and operators' log searches rely on them. Renaming
  public test-imported functions is fine if the tests are updated in the same
  commit.
- Remove the unreachable list check and its test.
- `Secret` validator: raise `ValueError`, and reject when both `value` and
  `file` are not `None` (behaviour change: the odd both-set-with-empty-value
  request now gets a 422 instead of sealing an empty string).
- Rename `Data` to `SealingRequest` (JSON unchanged).

**Verify.** Unit tests green; add a test with a fake kubeseal script (a shell
script in `tmp_path` that echoes its stdin) proving value and file payloads
reach stdin byte-exact and that a non-zero exit becomes a 500.

### Task 4: Kubernetes resolvers and router wiring

**Findings.** Both resolvers call `config.load_incluster_config()` and
`fix_incluster_bearer_token()` on every request and duplicate that preamble;
`kubernetes.py` chooses mock vs. real resolvers at import time while
`kubeseal.py` checks `settings.mock_enabled` per call (two mock strategies);
the namespace resolver builds a list with a manual `append` loop and has two
mypy errors; the sealed-secret resolver has one.

**Do.**
- One cached helper (e.g. in `kubernetes_utils.py`) that loads the in-cluster
  config and applies the bearer-token fix once, used by both resolvers.
- Fix the three mypy errors with real narrowing (skip namespaces without
  metadata/name), not `# type: ignore`.
- Keep the module attributes `kubernetes.namespace_resolver` and
  `kubernetes.sealed_secret_resolver` (tests replace them), but select them
  through one small function so the mock decision reads the same way as in
  the sealing code.

**Verify.** Unit tests green; `mypy kubeseal_webgui_api` reports 0 errors.

### Task 5: Consistency, lint and dependency hygiene

**Do.**
- One logger name: export `LOGGER_NAME` (already defined, unused elsewhere)
  and use it in all six modules that hard-code `"kubeseal-webgui"`.
- Modern typing everywhere (`list[str]`, `X | None`); `ruff check .` must be
  clean, `black --check .` and `isort --check .` must pass. Set
  `target-version = "py311"` to match `python = ">=3.11"`.
- Remove unused runtime dependencies `Jinja2` and `JSON-log-formatter`
  (no import anywhere; `PyYAML` stays, uvicorn needs it for the YAML log
  config) and refresh `poetry.lock`. If the lock cannot be refreshed in the
  sandbox, leave both files untouched and note it.
- `pytest.mark.container()` → `pytest.mark.container` etc. only if ruff asks
  for it.

**Verify.** All baseline API checks green/clean.

---

## Phase 3 — Vue UI

### Task 6: Formatting baseline and dev proxy fix

**Findings.** `npm run format` exists but was never applied: all 18 source
files fail `prettier --check`, and `Secrets.vue` mixes quote styles and
semicolons within one file. `npm run lint` always runs with `--fix`, so there
is no check-only command for CI. The Vite dev proxy regex
(`^/(secrets$|namespaces$|config$|docs|openapi\.json)`) does not match
`/sealed-secrets/...`, so the "import existing sealed secret" feature cannot
reach a local API in development (nginx has the route).

**Do.** Run prettier once over `ui/src` as a formatting-only commit (no manual
edits in that commit). Add scripts `lint:check` (`eslint .`) and
`format:check`. Add `sealed-secrets` to the dev proxy.

**Verify.** ESLint clean, `prettier --check` clean, build ok, E2E green.

### Task 7: Remove dead code and framework leftovers

**Findings.**
- `main.js` registers every Vuetify component and directive
  (`import * as components`) although `vite-plugin-vuetify` auto-import is
  enabled. This defeats tree-shaking (798 kB JS / 886 kB CSS).
- `assets/styles.css`: unused utilities (`.glass`, `.glass-strong`,
  `.bg-gradient-*`, `.text-gradient-secondary`, `.text-gradient-warm`,
  `.transition-all`, `.transition-slow`, `.hover-*`, `.pulse`, `.shimmer`,
  `.gradient-border`, `.modern-btn-gradient`, `.slide-up-*`) and unused custom
  properties (spacing and font-size scales, several gradients/shadows).
- `Secrets.vue` carries ~90 lines of **unscoped** global CSS, including dead
  rules (`.helper-info`, `.key-code`, `.slide-up-*`) and second, conflicting
  definitions of `.encrypt-btn` and `.fade-*` that also exist in `styles.css`
  (both with `!important`).
- Vuetify 2 / Bootstrap leftovers that do nothing today: `top` on
  `v-snackbar`, `left` / `small` on `v-icon`, `dense` on `v-file-input`,
  `:select-size`, `:plain`, `trim`, `align="center"` on `v-container`,
  classes `text-muted` and `navbar-brand`, `.app-config`, the empty
  `<style scoped>` in `App.vue`, the `/* Removed text styles */` comment.
- `AppConfig.vue`: `errorMessage` is written and never read.
- `package.json`: `core-js`, `@rushstack/eslint-patch` and
  `vue-eslint-parser` are not referenced; `@fontsource/roboto` is pinned to
  `"*"`.

**Do.** Remove all of the above. Before deleting a CSS rule or prop, grep for
its use; before removing a Vuetify prop, confirm in the installed Vuetify
version that it is not a prop of that component. For the two duplicated rule
sets keep the declarations that currently win in the browser (check computed
styles before and after) and move global rules into `styles.css`. Pin
`@fontsource/roboto` to the installed major with a caret. Update
`package-lock.json` with `npm install --legacy-peer-deps` (the flag CI uses).

**Verify.** Build ok and bundle sizes reported in the commit message; E2E
green; take before/after screenshots (light and dark, form and result view,
desktop and 390 px wide) and confirm there is no visual difference beyond
anti-aliasing. If removing the global Vuetify registration breaks any
component, revert only that part and note it.

### Task 8: Shared constants and a stable secret-entry model

**Findings.**
- Magic values repeated across files: the scope strings
  (`['strict', 'namespace-wide'].indexOf(scope) === -1` three times in
  `SecretFormInputs.vue`, two `.includes` variants in `Secrets.vue`),
  `1048576`, the 1 MB message (three copies), `2000`, `600`.
- The empty row literal `{ key: '', value: '', file: [] }` appears six times.
  `file` is `[]` when empty and a `File` otherwise, which forces
  `instanceof Blob || instanceof File` checks (redundant: every `File` is a
  `Blob`) in three places.
- Rows are keyed by array index (`:key="counter"`), so removing a row moves
  validation and copy state to the wrong row.
- `id="secretKey"`, `id="secretValue"`, `id="fileInput"` are repeated for
  every row: duplicate DOM ids (measured: 2 after one "Add").
- Per-row state is spread over parallel arrays passed as props (`hasValue`,
  `hasFile`, `fileErrors`), and `SecretsList` emits `update:secrets` with an
  `{ index, field, value }` payload, which looks like `v-model` but is not.
  `validateFile` reassigns the whole array to force an update.

**Do.**
- `src/constants.js`: `SCOPES`, a `scopeNeedsNamespace(scope)` /
  `scopeNeedsName(scope)` pair mirroring the API's `Scope` methods,
  `MAX_FILE_SIZE_BYTES`, message and timing constants. Keep the 600 ms
  post-seal delay (deliberate UX) but name it.
- `createSecretEntry()` factory returning `{ id, key, value, file: null }`
  with a unique `id`; use `entry.id` as `v-for` key; derive `hasValue` /
  `hasFile` inside `SecretInput` from the entry; keep the file error on the
  entry or in a map keyed by id.
- Ids become `secretKey-<index>` etc.; update the E2E selectors accordingly.
- Replace the `{ index, field, value }` event with explicit
  `update-entry` (or per-field `v-model` on `SecretInput`).

**Verify.** ESLint clean, E2E green, plus a new E2E test: add three rows, fill
them, remove the middle one, assert the remaining two keep their values and no
duplicate ids exist.

### Task 9: Extract pure logic from `Secrets.vue` and unit-test it

**Finding.** `Secrets.vue` is 793 lines with 25 refs and mixes eight concerns:
config loading, validation rules, clipboard access, favourites in
localStorage, the import-existing-secret flow, YAML rendering, error state and
global CSS. None of the logic is unit-tested.

**Do.**
- `src/utils/validation.js`: `isDnsLabel`, `isDnsSubdomain` and the Vuetify
  rule arrays. Keep the regular expressions and messages as they are. Replace
  `var`, and make `validDnsSubdomain` return a boolean for empty input instead
  of `undefined`.
- `src/utils/clipboard.js`: `isClipboardSupported`, `copyToClipboard`
  (unchanged fallback behaviour for plain-HTTP deployments).
- `src/utils/sealedSecretYaml.js`: build the full SealedSecret manifest as a
  string from `{ name, namespace, scope, entries }`.
- `src/composables/useFavoriteNamespaces.js` (guarded localStorage, as today)
  and `src/composables/useSealedSecretImport.js` (menu state, loading, the
  confirm-overwrite flow and its watchers).
- Add `vitest` as a dev dependency with an `npm test` script and unit tests
  for validation (the valid/invalid names already listed in
  `ui/tests/test_ui.py`, 63/253 length limits), YAML rendering (the exact
  strings pinned in Task 1) and `describeDetail` / `HttpError` formatting in
  `utils/http.js`.

**Verify.** `npm test` green, ESLint clean, E2E green. `Secrets.vue` should end
up as orchestration only; report its new line count.

### Task 10: Stop copying from the DOM

**Finding.** The manifest only exists as whitespace-sensitive template text in
`SealedSecretCard.vue`. To copy it, `Secrets.vue` reaches through two
`defineExpose`d refs
(`secretsResultsRef.value?.sealedSecretCardRef?.$refs?.sealedSecretRef`) and
reads `innerText`. Copy/"copied" state (`isCopiedMain`, `copiedIndividual`,
snackbar message, timers) is owned by the grandparent and passed down through
two levels.

**Do.** Compute the manifest once with the Task 9 function, pass the string to
`SealedSecretCard` for display and copy that same string. Remove both
`defineExpose`s. Move the "copied" indicator state into a small
`useCopyFeedback` composable or into the card components; the parent only
needs a `copied` / `copy-failed` event for the snackbar. Extract the copy
button that is duplicated in `SealedSecretCard` and `SecretKeyCard` (it also
sets the icon twice, via the `icon` prop and a child `v-icon`) into one
`CopyButton` component.

**Verify.** The exact-text assertions from Task 1 still pass unchanged; add an
E2E assertion that the clipboard receives the same text
(grant `clipboard-read`/`clipboard-write` in the Playwright context).

### Task 11: Configuration loading and API modules

**Findings.**
- `config.json` is fetched twice on every page load (`Secrets.vue` and
  `AppConfig.vue`), plus a lazy re-fetch in `getConfig()`.
- `useConfig` / `useSecrets` hold no reactive state; they are API modules
  wrapped in a function. `fetchAppConfig` returns `{ configs, success: true }`
  where `success` can only be `true`. snake_case names leak into JS
  (`data_config`, `kubeseal_webgui_ui_version`).
- `fetchDisplayName` is an `async` function that performs one assignment;
  `fetchEncodedSecrets` does not fetch encoded secrets, it seals them;
  `JSON.stringify(requestObject, null, "\t")` pretty-prints a request body.
- `isEnabled` parses a boolean from a string because the Helm-rendered
  `config.json` may contain either.
- `import.meta.env.VITE_MOCK_NAMESPACES` is a truthiness check on a string
  (`"false"` enables mocks).

**Do.** One module that loads `config.json` once (cached promise) and returns
a normalised object (`apiUrl`, `displayName`, `importEnabled`, `uiVersion`,
`apiVersion`); an `api` module with `fetchNamespaces`, `fetchSealedSecrets`,
`sealSecrets`, `fetchApiConfig`. Keep `useConfig.js` / `useSecrets.js` only if
they add something; otherwise delete them. Compare the env flag with
`'true'`. `AppConfig.vue` keeps showing the same chips with the same keys
(`kubesealVersion`, `uiVersion`, `apiVersion`) in the same order.

**Verify.** E2E green; assert in an E2E test that `config.json` is requested
exactly once per page load.

### Task 12: Small components

**Findings and fixes.**
- The info-icon tooltip block is copied five times (four in
  `SecretFormInputs.vue`, one in `SecretsList.vue`) → one `InfoTooltip`
  component with a default slot.
- `SecretFormInputs.vue` filters favourites twice (`sortedNamespaces`,
  `lastFavoriteNamespace`) → one computed. The favourite toggle is a bare
  `v-icon` with a click handler: not focusable, no label → `v-btn` with
  `icon`, `aria-label` and `aria-pressed`, same look.
- `DarkMode.vue`: `isDarkModeEnabled()` reads a preference **and** switches the
  theme; localStorage is used unguarded (the logger and favourites guard it,
  privacy mode throws); `v-model` and `@change` both handle the toggle; the
  scoped `.v-icon` selector styles a child component's root by accident. →
  pure `readPreferredDark()`, guarded storage, a single watcher. If the
  installed Vuetify logs a deprecation for assigning `theme.global.name`,
  switch to the API it recommends.
- `AppLogo.vue`: Options API in a `<script setup>` code base, a `v-col`
  without a row, `href="#"` → `<script setup>`-style SFC, plain wrapper,
  `href="/"`.
- `App.vue`: inline styles → classes.

**Verify.** ESLint/prettier clean, unit + E2E green, before/after screenshots
as in Task 7, keyboard check: the favourite toggle is reachable with Tab and
toggles with Enter/Space.

---

## Phase 4 — Enforcement

### Task 13: Run the checks in CI

**Finding.** No workflow runs the API unit tests, ruff, mypy, ESLint or
prettier. Only the Playwright E2E suite and image builds run. That is how the
"documented test command fails" state went unnoticed.

**Do.** Add `.github/workflows/checks.yml` (pull_request + push to
main/master): API job (`poetry install`, ruff, black, isort, mypy,
`pytest -m "not container and not cluster"`), UI job (`npm ci
--legacy-peer-deps`, `npm run lint:check`, `npm run format:check`, `npm test`,
`npm run build`). Pin actions the same way the existing workflows do. Update
`docs/development.md` and `CONTRIBUTING.md` where commands changed.

**Commit this task separately and last.** Pushing workflow files can be
rejected when the push credential lacks the workflow permission; if that
happens, drop this commit from the branch, push the rest and report it.

---

## Explicitly out of scope (needs a maintainer decision)

- **Server-side name validation is looser than the UI's.** `valid_k8s_name`
  accepts `_` and 253 characters for namespaces; the UI enforces RFC 1123
  labels (63) for namespaces and subdomains for names. Tightening the API is a
  breaking change for direct API clients, and a test pins the current
  behaviour (`some.dots.or_underscore` is valid).
- `allow_origins=["http://localhost:8080"]` hard-coded in `app.py`, while a
  test sets an `ORIGIN_URL` env variable that nothing reads.
- The 1.48 MB `logo-2025.png`, rendered 200 px high inside a 100 px app bar.
- Theme `error` colour equals `secondary` (orange).
- `api/pyproject.toml` / `ui/package.json` say version 4.5.4 while the chart's
  appVersion is 4.14.0 (`dev/bump_version.sh` is evidently not part of the
  release flow).
- The mock namespace word lists are duplicated in Python and JavaScript.
- Migrating the UI to TypeScript.

## Execution notes

All 13 tasks were worked through in order. No task was reverted. No existing
test was deleted, skipped or loosened, except the unreachable "list of dicts"
test that Task 3 names.

### Status and commits

| Task | Status | Commit(s) |
|---|---|---|
| 1 E2E safety net | done | `895bc43` |
| 2 `app_config.py` | done | `492f115` |
| 3 Sealing pipeline | partly done (no `Data` rename) | `88093b9` |
| 4 Resolvers and wiring | done, caching adapted | `935a9ad`, `fa721c2` |
| 5 Consistency, lint, dependencies | done | `2bf564d` |
| 6 Prettier, check scripts, dev proxy | done, as two commits | `c861a59`, `df799dc` |
| 7 Dead code | done, one package kept | `d7b1db0` |
| 8 Constants and entry model | done | `caf3184` |
| 9 Extract and unit-test logic | done | `5da2640` |
| 10 Stop copying from the DOM | done | `3d17d94` |
| 11 Config loading and API modules | done | `8a8b1ca` |
| 12 Small components | done, keyboard access adapted | `b238446`, `3e4a225` |
| 13 CI checks | done, pushed | `97a8529` (docs), `b895cb7` (workflow) |

### Deviations from the plan, and why

- **Task 3: `Data` was not renamed to `SealingRequest`.** The class name is
  the schema name in `/openapi.json`. An existing test
  (`test_secret_name_keeps_its_json_key`) reads
  `components.schemas.Data`, and generated API clients see that name, so
  "JSON unchanged" does not hold for the rename.
- **Task 4: the in-cluster config is not cached unconditionally.**
  `Dockerfile.api` installs with `pip install ./src`, not from `poetry.lock`,
  so the image gets whatever `kubernetes>=35` is current. A client that still
  needs `fix_incluster_bearer_token` refreshes a rotated service account token
  only under the old `authorization` key; loading once would leave the copied
  token stale after about an hour. `ensure_incluster_config()` therefore
  loads once only when the fix was not needed and reloads per call otherwise.
  A test with the real loader of the locked client (37.0.2) proves that a
  rotated token file is picked up after a single load.
- **Task 4: the resolvers are chosen per call, not at import.** The module
  attributes `kubernetes.namespace_resolver` / `sealed_secret_resolver` still
  exist and tests still replace them; they are now two small functions that
  check `settings.mock_enabled`, like the sealing code.
- **Task 6 is two commits**: the plan asks for a formatting-only commit and
  for script/proxy changes; mixing them would have defeated the first.
- **Task 7: `vue-eslint-parser` was kept.** It is a peer dependency of
  `eslint-plugin-vue`, and `npm ci --legacy-peer-deps` does not install peers
  by itself. Also removed, although not listed: `src/plugins/vuetify.js`
  (imported nowhere).
- **Tasks 7 and 9: `package-lock.json` was edited minimally** instead of
  taking the output of the local npm 10, which also dropped every `libc`
  field and rewrote `dev` flags of unrelated packages. The result only
  removes `core-js` and `@rushstack/eslint-patch` and adds vitest's 19
  packages; `npm ci --legacy-peer-deps` accepts it in a fresh clone.
- **Task 11: files are read with `Blob.arrayBuffer()`** instead of
  `FileReader.readAsDataURL` plus string splitting, so that the request
  building can be unit-tested in Node. The base64 sent is the same (asserted
  in the E2E test).
- **Task 12: the favourite toggle is reached with the arrow keys, not Tab.**
  Vuetify closes the autocomplete menu on Tab, by design. Inside the list the
  arrow keys visit each item and then its toggle; Enter and Space toggle it
  without selecting the namespace. The plan's finding that the old `v-icon`
  was not focusable was not accurate for Vuetify 4.3 (it rendered
  `role="button" tabindex="0"`), but it had no label, no pressed state and no
  key handling.
- **Task 12 is preceded by an unplanned bug fix (`b238446`).** Favourite
  namespaces did not work at all at the baseline: Vuetify 4 passes the raw
  item to the `item` slot, the template read `item.value` (undefined), so any
  click stored `[null]`, filled every heart and sorted nothing. The toggle
  rewrite needed the right value for `aria-pressed`, so this was fixed first,
  in its own commit, with an E2E test.
- **Task 13: `mypy .` is not what CI runs.** The documented `mypy .` fails on
  `tests/test_logging.py` (PyYAML has no stubs installed) at the baseline
  too; CI and the docs now use `mypy kubeseal_webgui_api`. Node is not pinned
  with `actions/setup-node` because no existing workflow uses it and its
  current major could not be checked from the sandbox; like
  `frontend-tests.yml`, the job uses the runner's Node. Docs changes are in
  a separate commit so that they would have survived dropping the workflow
  commit.

### Measured results

Same commands as in "Verified baseline", run after the last commit.

| Check | Baseline | Result |
|---|---|---|
| API unit tests (`-m "not container and not cluster"`) | 64 passed, 6 deselected | 136 passed, 6 deselected, with and without `KUBESEAL_BINARY`; same on Python 3.11 |
| API tests as documented (`poetry run pytest`) | collection error | collects; 139 passed, 3 failed (the three `container`/`cluster` tests that need a real kubeseal binary) |
| API import in mock mode | RuntimeError | succeeds |
| ruff | 39 findings | clean |
| mypy `kubeseal_webgui_api` | 3 errors | 0 errors |
| black / isort | 2 / 2 files fail | pass |
| ESLint | clean | clean |
| Prettier (`src/`, and `tests/unit/`) | all 18 files fail | clean |
| UI build | JS 798 kB, CSS 886 kB | JS 429 kB (gzip 145 kB), CSS 692 kB (gzip 112 kB) |
| UI E2E | 6 passed | 25 passed (three consecutive runs) |
| UI unit tests (`npm test`) | none | 153 passed in 9 files |
| `Secrets.vue` | 793 lines | 393 lines |

Screenshots (dev server and production build; light/dark; 1280 px and
390 px; empty form, namespace menu, filled form, import menu, result view,
error snackbar) were compared pixel by pixel after Tasks 7 to 12. Apart from
the namespace menu, whose content changed with the favourites fix, the
production build after Task 12 is identical to the one before Task 7; the
namespace menu differs from its state after the fix by at most 14
anti-aliased pixels.

### Behaviour changes

Intended by the plan:

- `KUBESEAL_AUTOFETCH` is a boolean. `False`, `0`, `no`, `off` now switch
  auto-fetch off (they switched it on before). A value that is not a boolean
  stops the API at start-up with a pydantic validation error; before it
  meant "on".
- Mock mode needs no kubeseal binary; importing the API package runs nothing.
  An unusable binary is still fatal at start-up, with the same message, but
  is reported by the ASGI lifespan ("Application startup failed", exit code
  3) instead of as an import error.
- `KUBESEAL_CERT` unset: sealing used `/dev/null`, now the documented
  `/kubeseal-webgui/cert/kubeseal-cert.pem`. The chart always sets it.
- `POST /secrets` rejects an entry in which both `value` and `file` are
  present, even if one is the empty string (422). The validation error has
  type `value_error` and a message starting with "Value error," instead of
  `assertion_error` / "Assertion failed,".
- Input ids are `secretKey-<n>`, `secretValue-<n>`, `fileInput-<n>`.
- The logo links to `/` instead of `#`: a click loads the start page and
  with it an empty form.
- `VITE_MOCK_NAMESPACES` only enables the mock when it is `true`.
- The dev server proxies `/sealed-secrets/...` to the API.

Side effects of the refactoring (all small, none on the happy path):

- The start-up log line prints `certificate auto-fetch: False/True` instead
  of the raw string.
- `GET /namespaces` and `GET /sealed-secrets/{ns}`: a response of an
  unexpected type yields a warning and an empty list instead of an HTTP 500;
  namespace objects without metadata or name are skipped. Mock mode is
  evaluated per request.
- `MOCK_NAMESPACE_COUNT` and the other settings can only be set through the
  environment variables of `AppSettings`; nothing else reads `os.environ`.
- The sealing request body is compact JSON instead of tab-indented.
- `config.json` is requested once per page load instead of twice. The display
  name appears as soon as it is loaded, not after the namespace list.
- The file-size rule no longer throws `files.some is not a function` in the
  browser console when a file is selected. A file error disappears together
  with its row.
- Removing a row keeps the validation state of the other rows with them.
- The UI works when `localStorage` is blocked; writing favourites is guarded.
- The copy button's "Copied!" state uses one timer per button.
- No Vue/Vuetify warnings are left in the browser console (duplicate input
  names, `theme.global.name`, `dense`).

Not planned, done deliberately: favourite namespaces work again (see above).

### Found, not changed

- After a failed seal the Encrypt button stays disabled until the page is
  reloaded or a valid file is selected: `hasErrorMessage` is only cleared in
  those two places. The same holds after a failed copy. Existing behaviour,
  now visible in `test_failed_sealing_keeps_the_form_and_shows_the_error`.
- Right after toggling a favourite, the open list can stay scrolled so that
  the new first entry is above the visible part (Vuetify virtual scroll);
  re-opening the list shows it. The E2E tests re-open the list for that
  reason.
- The result card renders its title below the manifest (`v-card-title`
  after the `#text` slot), and on a 390 px screen the dark mode switch
  overlaps the logo. Both unchanged.
- `docs/development.md` describes `main.yml` as "lint, tests, basic builds";
  it is a manually triggered image build.
- `<v-footer inset width="auto">` in `App.vue`: neither is a prop of
  Vuetify 4's `VFooter`. Left alone because it was not on the list.

### Not verified by running

- `checks.yml` has not run on GitHub: no pull request was opened and the
  workflow does not trigger on this branch. Its commands were run in a fresh
  clone with Python 3.11 and 3.13 and the local Node 22; the action versions
  are the ones the other workflows use.
- `Dockerfile.api` / `Dockerfile.ui` builds, the Helm chart and a real
  cluster (in-cluster config, RBAC, a real `kubeseal` binary) were not
  exercised. The sealing pipeline was tested against a stand-in script, the
  token refresh against the real client code with fake token files.
- The typo check (`crate-ci/typos`) was not run locally.
- The client-version branch of `ensure_incluster_config()` that reloads on
  every call was tested with a simulated old client, not a real 36.x one.
