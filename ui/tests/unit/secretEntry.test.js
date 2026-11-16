import { describe, expect, it } from 'vitest'
import {
  createSecretEntry,
  entryHasFile,
  entryHasValue,
  findDuplicateKeys,
  formatFileSize,
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

describe('createSecretEntry with content', () => {
  it('takes a value or a file, as used when entries are added from files', () => {
    const file = someFile()
    expect(createSecretEntry({ key: 'a', value: 'x' })).toMatchObject({ key: 'a', value: 'x' })
    const withFile = createSecretEntry({ key: 'b', file })
    expect(withFile.file).toBe(file)
    expect(isEntryComplete(withFile)).toBe(true)
  })
})

describe('findDuplicateKeys', () => {
  const keys = (...names) => names.map((key) => createSecretEntry({ key }))

  it('finds nothing without duplicates', () => {
    expect(findDuplicateKeys(keys('a', 'b', 'c')).size).toBe(0)
    expect(findDuplicateKeys([]).size).toBe(0)
  })

  it('returns every key that occurs more than once, once', () => {
    expect(findDuplicateKeys(keys('a', 'b', 'a', 'b', 'a', 'c'))).toEqual(new Set(['a', 'b']))
  })

  it('ignores empty keys', () => {
    expect(findDuplicateKeys(keys('', '', 'a')).size).toBe(0)
  })

  it('compares keys exactly, since Kubernetes keys are case sensitive', () => {
    expect(findDuplicateKeys(keys('Key', 'key')).size).toBe(0)
  })
})

describe('formatFileSize', () => {
  it.each([
    [0, '0 B'],
    [512, '512 B'],
    [1024, '1 KB'],
    [1536, '1.5 KB'],
    [1024 * 1024, '1 MB'],
    [10 * 1024 * 1024 * 1024 * 1024, '10240 GB']
  ])('formats %i bytes as %s', (bytes, text) => {
    expect(formatFileSize(bytes)).toBe(text)
  })
})
