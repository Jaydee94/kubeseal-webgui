// Sealing one secret for several namespaces: the namespaces are part of what a
// value is sealed for, so every namespace needs a sealing request of its own.

import { isDnsLabel } from '@/utils/validation'

/**
 * The namespaces to seal for: the main one first, then the additional ones.
 * Empty entries and repeats are dropped, so a namespace is never sealed twice.
 */
export function namespacesToSeal(main, additional = []) {
  const unique = new Set([main, ...additional].filter((name) => !!name))
  return [...unique]
}

/**
 * The first of the names that is not a valid namespace name, or `''`. Empty
 * entries are skipped: they are never sealed for (see namespacesToSeal), and
 * `''` must only mean "no invalid name".
 */
export function firstInvalidNamespace(names) {
  return names.find((name) => !!name && !isDnsLabel(name)) ?? ''
}
