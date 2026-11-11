// Runtime configuration of the UI. `config.json` is rendered by the Helm chart
// (see public/config.json for the development version), so one container
// image works in every environment.

import { requestJson } from '@/utils/http'

let pendingConfig = null

/** The chart may render a flag as a boolean or as a string. */
export function toBoolean(value) {
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'string') {
    return ['true', '1', 'yes', 'on'].includes(value.toLowerCase())
  }
  return false
}

/** Translate the snake_case keys of config.json into the shape the UI uses. */
export function normalizeConfig(raw) {
  return {
    apiUrl: raw?.api_url ?? '',
    displayName: raw?.display_name ?? '',
    importEnabled: toBoolean(raw?.enable_existing_sealed_secret_loading),
    uiVersion: raw?.kubeseal_webgui_ui_version,
    apiVersion: raw?.kubeseal_webgui_api_version
  }
}

/**
 * Load config.json. It is requested once and shared by all callers; a failed
 * request is not remembered, so the next call tries again.
 */
export function loadConfig() {
  if (!pendingConfig) {
    const request = requestJson('/config.json').then(normalizeConfig)
    pendingConfig = request
    request.catch(() => {
      if (pendingConfig === request) pendingConfig = null
    })
  }
  return pendingConfig
}
