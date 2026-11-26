// Calls to the kubeseal-webgui API. The API URL comes from config.json.

import { Base64 } from 'js-base64'
import { loadConfig } from '@/config'
import { requestJson } from '@/utils/http'
import { mockNamespacesResolver } from '@/utils/mockData'
import { entryHasFile } from '@/utils/secretEntry'

const MOCK_NAMESPACE_COUNT = 10

/**
 * The URL of an API endpoint (`path` without a leading "/"). Without a
 * configured API URL the result is relative to the page, so the API is found
 * next to the UI, also under a path prefix.
 */
export function joinApiUrl(baseUrl, path) {
  if (!baseUrl) {
    return path
  }
  return `${baseUrl.replace(/\/+$/, '')}/${path}`
}

async function apiUrl(path) {
  const { apiUrl: baseUrl } = await loadConfig()
  return joinApiUrl(baseUrl, path)
}

/** Names of the namespaces in the cluster (made up with VITE_MOCK_NAMESPACES=true). */
export async function fetchNamespaces() {
  if (import.meta.env.VITE_MOCK_NAMESPACES === 'true') {
    return mockNamespacesResolver(MOCK_NAMESPACE_COUNT)
  }
  return requestJson(await apiUrl('namespaces'))
}

/**
 * The clusters a secret can be sealed for, as [{ name, inCluster, fingerprint }, ...].
 * The first one is the default. `inCluster` marks the one the API runs in:
 * only for it the namespaces and SealedSecrets can be read.
 */
export async function fetchClusters() {
  try {
    return await requestJson(await apiUrl('clusters'))
  } catch (error) {
    // The dev server runs without an API (VITE_MOCK_NAMESPACES): one cluster.
    if (import.meta.env.VITE_MOCK_NAMESPACES === 'true') {
      return []
    }
    throw error
  }
}

/** The SealedSecrets of a namespace as [{ name, keys }, ...]. */
export async function fetchSealedSecrets(namespace) {
  return requestJson(await apiUrl(`sealed-secrets/${encodeURIComponent(namespace)}`))
}

/** Settings of the API, e.g. { kubesealVersion }. */
export async function fetchApiConfig() {
  return requestJson(await apiUrl('config'))
}

// A row holds a file or a text value. Anything without a file is sent as a
// value, an empty one included, so a row is never read as a missing file.
async function toRequestEntry(entry) {
  if (entryHasFile(entry)) {
    const content = new Uint8Array(await entry.file.arrayBuffer())
    return { key: entry.key, file: Base64.fromUint8Array(content) }
  }
  return { key: entry.key, value: Base64.encode(entry.value) }
}

/**
 * Seal the entries (each with a `value` or a `file`) and return the sealed
 * values as [{ key, value }, ...].
 */
export async function sealSecrets({ secretName, namespaceName, scope, entries, cluster }) {
  const sealingRequest = {
    secret: secretName,
    namespace: namespaceName,
    scope,
    // Left out for an API that lists no clusters: it then uses its only one.
    ...(cluster ? { cluster } : {}),
    secrets: await Promise.all(entries.map(toRequestEntry))
  }

  // requestJson logs method, URL and status only -- never this body, which
  // contains the cleartext secrets.
  return requestJson(await apiUrl('secrets'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(sealingRequest)
  })
}
