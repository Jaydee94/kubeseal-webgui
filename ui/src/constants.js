// Values shared between components. The scope helpers mirror `Scope` in the
// API (api/kubeseal_webgui_api/routers/models.py).

export const SCOPE_STRICT = 'strict'
export const SCOPE_CLUSTER_WIDE = 'cluster-wide'
export const SCOPE_NAMESPACE_WIDE = 'namespace-wide'

// In the order they are offered in the scope selection.
export const SCOPES = [SCOPE_STRICT, SCOPE_CLUSTER_WIDE, SCOPE_NAMESPACE_WIDE]
export const DEFAULT_SCOPE = SCOPE_STRICT

/** Only the strict scope seals the secret for one specific name. */
export function scopeNeedsName(scope) {
  return scope === SCOPE_STRICT
}

/** Cluster-wide secrets can be unsealed in any namespace. */
export function scopeNeedsNamespace(scope) {
  return scope !== SCOPE_CLUSTER_WIDE
}

export const MAX_FILE_SIZE_BYTES = 1024 * 1024
export const FILE_TOO_LARGE_MESSAGE = 'File size should be less than 1 MB!'

export const ERROR_SNACKBAR_TIMEOUT_MS = 5000
export const CLIPBOARD_SNACKBAR_TIMEOUT_MS = 3000
// How long a copy button shows its "copied" state.
export const COPIED_FEEDBACK_MS = 2000
// Deliberate pause after sealing so that the switch to the result view is
// noticeable instead of an abrupt flicker.
export const POST_SEAL_DELAY_MS = 600
