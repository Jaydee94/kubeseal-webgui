import { describe, expect, it } from 'vitest'
import {
  createSecretEntry,
  entryHasFile,
  entryHasValue,
  isEntryBlank,
  isEntryComplete
} from '@/utils/secretEntry'

const someFile = () => new Blob(['content'])

describe('createSecretEntry', () => {
  it('creates a blank entry', () => {
    const entry = createSecretEntry()
    expect(entry).toMatchObject({ key: '', value: '', file: null, fileError: '' })
    expect(isEntryBlank(entry)).toBe(true)
    expect(isEntryComplete(entry)).toBe(false)
  })

  it('gives every entry its own id', () => {
    const ids = [createSecretEntry(), createSecretEntry(), createSecretEntry({ key: 'a' })].map(
      (entry) => entry.id
    )
    expect(new Set(ids).size).toBe(3)
  })

  it('takes a key, as used when importing an existing sealed secret', () => {
    const entry = createSecretEntry({ key: 'API_KEY' })
    expect(entry.key).toBe('API_KEY')
    expect(isEntryBlank(entry)).toBe(false)
    expect(isEntryComplete(entry)).toBe(false)
  })
})

describe('entry state', () => {
  it('is complete with a key and a value', () => {
    const entry = { ...createSecretEntry({ key: 'k' }), value: 'v' }
    expect(entryHasValue(entry)).toBe(true)
    expect(entryHasFile(entry)).toBe(false)
    expect(isEntryComplete(entry)).toBe(true)
  })

  it('is complete with a key and a file', () => {
    const entry = { ...createSecretEntry({ key: 'k' }), file: someFile() }
    expect(entryHasValue(entry)).toBe(false)
    expect(entryHasFile(entry)).toBe(true)
    expect(isEntryComplete(entry)).toBe(true)
  })

  it('is neither blank nor complete with a value but no key', () => {
    const entry = { ...createSecretEntry(), value: 'v' }
    expect(isEntryBlank(entry)).toBe(false)
    expect(isEntryComplete(entry)).toBe(false)
  })

  it('is not blank with only a file', () => {
    expect(isEntryBlank({ ...createSecretEntry(), file: someFile() })).toBe(false)
  })
})
