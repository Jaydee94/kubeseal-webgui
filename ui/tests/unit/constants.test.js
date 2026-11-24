import { describe, expect, it } from 'vitest'
import { DEFAULT_SCOPE, SCOPES, scopeNeedsName, scopeNeedsNamespace, toScope } from '@/constants'

// Has to agree with `Scope.needs_name` / `Scope.needs_namespace` in the API.
describe('scopes', () => {
  it('offers the three scopes of sealed secrets, strict first', () => {
    expect(SCOPES).toEqual(['strict', 'namespace-wide', 'cluster-wide'])
    expect(DEFAULT_SCOPE).toBe('strict')
  })

  it.each(SCOPES)('%s is a scope', (scope) => {
    expect(toScope(scope)).toBe(scope)
  })

  it.each(['', 'Strict', 'cluster', undefined, null, 42])('%j is not a scope', (value) => {
    expect(toScope(value)).toBe(DEFAULT_SCOPE)
  })

  it.each([
    ['strict', true, true],
    ['namespace-wide', false, true],
    ['cluster-wide', false, false]
  ])('%s: needs name %s, needs namespace %s', (scope, needsName, needsNamespace) => {
    expect(scopeNeedsName(scope)).toBe(needsName)
    expect(scopeNeedsNamespace(scope)).toBe(needsNamespace)
  })
})
