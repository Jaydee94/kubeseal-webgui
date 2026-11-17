// Renders the SealedSecret manifest users copy into their repositories.
// The exact text is pinned by unit and E2E tests: change it deliberately.
// (The strict scope used to get an empty `annotations: {}` line; it is left
// out, because it is noise in a manifest that is meant to be committed.)

import { SCOPE_STRICT } from '@/constants'

const NO_NAME_PLACEHOLDER = '# no secret name given'
const NO_NAMESPACE_PLACEHOLDER = '# no namespace name given'

/**
 * The annotations flow mapping of a scope, or `null` for none: the strict
 * scope is the controller's default and needs no annotation.
 */
export function scopeAnnotations(scope) {
  if (scope === SCOPE_STRICT) {
    return null
  }
  return `{ sealedsecrets.bitnami.com/${scope}: "true" }`
}

/**
 * @param {object} manifest
 * @param {string} manifest.name secret name, may be empty outside the strict scope
 * @param {string} manifest.namespace may be empty for cluster-wide secrets
 * @param {string} manifest.scope one of SCOPES
 * @param {{key: string, value: string}[]} manifest.entries the sealed values
 * @returns {string} the manifest as YAML text
 */
export function renderSealedSecretYaml({ name, namespace, scope, entries }) {
  const annotations = scopeAnnotations(scope)
  const header = [
    'apiVersion: bitnami.com/v1alpha1',
    'kind: SealedSecret',
    'metadata:',
    `  name: ${name || NO_NAME_PLACEHOLDER}`,
    `  namespace: ${namespace || NO_NAMESPACE_PLACEHOLDER}`,
    ...(annotations === null ? [] : [`  annotations: ${annotations}`]),
    'spec:',
    // The space after the colon has always been part of the output.
    '  encryptedData: '
  ]
  const data = entries.map((entry) => `    ${entry.key}: ${entry.value}`)
  return `${header.join('\n')}\n${data.join('\n')}`
}

/** The download is named after the secret, or generically without a name. */
export function manifestFileName(name) {
  return `${name || 'sealed-secret'}.yaml`
}
