import { describe, expect, it } from 'vitest'
import { firstInvalidNamespace, namespacesToSeal } from '@/utils/namespaces'
import { manifestFileName } from '@/utils/sealedSecretYaml'

describe('namespacesToSeal', () => {
  it('puts the main namespace first and keeps the order of the others', () => {
    expect(namespacesToSeal('a', ['c', 'b'])).toEqual(['a', 'c', 'b'])
  })

  it('seals for the main namespace alone without additional ones', () => {
    expect(namespacesToSeal('a')).toEqual(['a'])
    expect(namespacesToSeal('a', [])).toEqual(['a'])
  })

  it('drops repeats, also of the main namespace, and empty entries', () => {
    expect(namespacesToSeal('a', ['b', 'a', '', 'b'])).toEqual(['a', 'b'])
  })

  it('has nothing to seal for without a main namespace', () => {
    expect(namespacesToSeal('', [])).toEqual([])
  })
})

describe('firstInvalidNamespace', () => {
  it('finds the first name that is no namespace name', () => {
    expect(firstInvalidNamespace(['ok', 'Not_Valid', 'also bad'])).toBe('Not_Valid')
  })

  it('finds an invalid name after an empty entry', () => {
    expect(firstInvalidNamespace(['', 'Not_Valid'])).toBe('Not_Valid')
    expect(firstInvalidNamespace(['', 'ok'])).toBe('')
  })

  it('finds nothing in valid names', () => {
    expect(firstInvalidNamespace(['a', 'team-b', '1'])).toBe('')
    expect(firstInvalidNamespace([])).toBe('')
  })
})

describe('manifestFileName with a namespace', () => {
  it('stays as it was without one', () => {
    expect(manifestFileName('db')).toBe('db.yaml')
    expect(manifestFileName('')).toBe('sealed-secret.yaml')
  })

  it('names the namespace', () => {
    expect(manifestFileName('db', 'team-a')).toBe('db-team-a.yaml')
    expect(manifestFileName('', 'team-a')).toBe('sealed-secret-team-a.yaml')
  })
})
