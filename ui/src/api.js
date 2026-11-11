// Calls to the kubeseal-webgui API. The API URL comes from config.json.

import { Base64 } from 'js-base64'
import { loadConfig } from '@/config'
import { requestJson } from '@/utils/http'
import { mockNamespacesResolver } from '@/utils/mockData'

const MOCK_NAMESPACE_COUNT = 10

async function apiUrl(path) {
  const { apiUrl: baseUrl } = await loadConfig()
  return `${baseUrl}${path}`
}

/** Names of the namespaces in the cluster (made up with VITE_MOCK_NAMESPACES=true). */
export async function fetchNamespaces() {
  if (import.meta.env.VITE_MOCK_NAMESPACES === 'true') {
    return mockNamespacesResolver(MOCK_NAMESPACE_COUNT)
  }
  return requestJson(await apiUrl('/namespaces'))
}

/** The SealedSecrets of a namespace as [{ name, keys }, ...]. */
export async function fetchSealedSecrets(namespace) {
  return requestJson(await apiUrl(`/sealed-secrets/${encodeURIComponent(namespace)}`))
}

/** Settings of the API, e.g. { kubesealVersion }. */
export async function fetchApiConfig() {
  return requestJson(await apiUrl('/config'))
}

async function toRequestEntry(entry) {
  if (entry.value) {
    return { key: entry.key, value: Base64.encode(entry.value) }
  }
  const content = new Uint8Array(await entry.file.arrayBuffer())
  return { key: entry.key, file: Base64.fromUint8Array(content) }
}

/**
 * Seal the entries (each with a `value` or a `file`) and return the sealed
 * values as [{ key, value }, ...].
 */
export async function sealSecrets({ secretName, namespaceName, scope, entries }) {
  const sealingRequest = {
    secret: secretName,
    namespace: namespaceName,
    scope,
    secrets: await Promise.all(entries.map(toRequestEntry))
  }

  // requestJson logs method, URL and status only -- never this body, which
  // contains the cleartext secrets.
  return requestJson(await apiUrl('/secrets'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(sealingRequest)
  })
}
