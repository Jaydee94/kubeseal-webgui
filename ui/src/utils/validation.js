// Name validation as Kubernetes defines it (RFC 1123) and the rule arrays the
// Vuetify inputs use. A rule returns `true` or the message to show.

import { FILE_TOO_LARGE_MESSAGE, MAX_FILE_SIZE_BYTES } from '@/constants'

const MAX_DNS_LABEL_LENGTH = 63
const MAX_DNS_SUBDOMAIN_LENGTH = 253

// Lower case alphanumerics and '-', starting and ending with an alphanumeric.
const DNS_LABEL = /^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$/
// Dot-separated labels of lower case alphanumerics and '-', each starting and
// ending with an alphanumeric.
const DNS_SUBDOMAIN = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$/

/** Kubernetes namespaces must be DNS labels, unlike secret names. */
export function isDnsLabel(name) {
  return typeof name === 'string' && DNS_LABEL.test(name)
}

/** Secret names may be DNS subdomains of up to 253 characters. */
export function isDnsSubdomain(name) {
  return (
    typeof name === 'string' && name.length <= MAX_DNS_SUBDOMAIN_LENGTH && DNS_SUBDOMAIN.test(name)
  )
}

/**
 * Turns arbitrary text into the closest valid secret name, or '' if nothing
 * usable is left. Used to suggest a fix, so it prefers a recognisable result
 * ("Claude_Test Secret" -> "claude-test-secret") over a minimal edit.
 */
export function toDnsSubdomain(text) {
  if (typeof text !== 'string') return ''
  const cleaned = cleanSubdomain(
    text
      .normalize('NFD')
      // Accents are dropped instead of replaced: "café" -> "cafe", not "caf-".
      .replace(/\p{M}/gu, '')
      .toLowerCase()
      .replace(/[^a-z0-9.]+/g, '-')
  )
  // Cutting at the limit can leave a '-' or '.' at the end, so clean again.
  return cleanSubdomain(cleaned.slice(0, MAX_DNS_SUBDOMAIN_LENGTH))
}

// Every label must start and end with an alphanumeric, so trim '-' per label
// and drop labels (and with them leading, trailing and repeated dots) that
// end up empty.
function cleanSubdomain(text) {
  return text
    .split('.')
    .map((label) => label.replace(/^-+|-+$/g, ''))
    .filter(Boolean)
    .join('.')
}

export function isFileTooLarge(file) {
  return file.size > MAX_FILE_SIZE_BYTES
}

/** The first message of a rule list for the value, or '' if all rules pass. */
export function firstRuleMessage(ruleList, value) {
  for (const rule of ruleList) {
    const result = rule(value)
    if (result !== true) return result
  }
  return ''
}

export const rules = {
  validNamespace: [
    (value) => !!value || 'Must not be empty',
    (value) => !value || value.length <= MAX_DNS_LABEL_LENGTH || 'Longer than 63 chars',
    (value) =>
      !value ||
      isDnsLabel(value) ||
      "Must consist of lower case alphanumerics or '-', and start and end with an alphanumeric"
  ],
  validDnsSubdomain: [
    (value) => !value || value.length <= MAX_DNS_SUBDOMAIN_LENGTH || 'Longer than 253 chars',
    (value) => !!value || 'Must not be empty',
    (value) =>
      (!!value && /^[a-z0-9-.]*$/.test(value)) ||
      'Invalid char. Must be one of lower chars, digits, dashes or dots.',
    (value) => (!!value && /^[a-z0-9]/.test(value)) || 'Must start with a lower char or digit',
    (value) => (!!value && /[a-z0-9]$/.test(value)) || 'Must end with a lower char or digit',
    (value) => isDnsSubdomain(value) || 'Not a valid DNS subdomain'
  ],
  // Outside the strict scope the secret name is not sealed into the secret.
  // It may stay empty, but a given name still has to be a valid one.
  optionalDnsSubdomain: [
    (value) => !value || value.length <= MAX_DNS_SUBDOMAIN_LENGTH || 'Longer than 253 chars',
    (value) =>
      !value ||
      isDnsSubdomain(value) ||
      "Must consist of lower case alphanumerics, '-' or '.', and start and end with an alphanumeric"
  ],
  validSecretKey: [
    (value) => !!value || 'Must not be empty',
    (value) =>
      (!!value && /^[a-z0-9_.-]*$/i.test(value)) ||
      'Invalid char. Must be one of lower chars, digits, dash, underscore or dot.'
  ],
  // A single-file input validates one File, a multi-file input an array.
  fileSize: [(files) => !files || ![files].flat().some(isFileTooLarge) || FILE_TOO_LARGE_MESSAGE]
}
