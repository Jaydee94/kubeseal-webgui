import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useDroppedFiles } from '@/composables/useDroppedFiles'
import { MAX_FILE_SIZE_BYTES } from '@/constants'
import { createSecretEntry } from '@/utils/secretEntry'

const file = (name, content, type = '') => new File([content], name, { type })

function setup(rows = [createSecretEntry()]) {
  const options = {
    entries: ref(rows),
    onSuccess: vi.fn(),
    onError: vi.fn(),
    onImported: vi.fn()
  }
  return { ...options, ...useDroppedFiles(options) }
}

const pairs = (entries) => entries.value.map(({ key, value }) => [key, value])

describe('useDroppedFiles', () => {
  it('turns a .env file into one entry per variable, replacing a blank row', async () => {
    const state = setup()

    await state.importDroppedFiles([file('.env', 'A=1\nB=two')])

    expect(pairs(state.entries)).toEqual([
      ['A', '1'],
      ['B', 'two']
    ])
    expect(state.onSuccess).toHaveBeenCalledWith('Imported 2 keys from .env')
  })

  it('passes only the new rows to onImported, not the whole list', async () => {
    const old = createSecretEntry({ key: 'old', value: 'x' })
    const state = setup([old])

    await state.importDroppedFiles([file('.env', 'A=1\nB=two')])

    expect(state.onImported).toHaveBeenCalledTimes(1)
    const [newRows] = state.onImported.mock.calls[0]
    expect(newRows.map(({ key }) => key)).toEqual(['A', 'B'])
    // the very rows that are now in the list, so that they can be focused
    expect(newRows).toEqual(state.entries.value.slice(1))
    expect(newRows).not.toContain(old)
  })

  it('counts an import as pending until its files are read', async () => {
    const state = setup()
    let release
    const slow = file('.env', 'A=1')
    slow.text = () => new Promise((resolve) => (release = () => resolve('A=1')))

    const done = state.importDroppedFiles([slow])
    expect(state.pendingImports.value).toBe(1)

    release()
    await done
    expect(state.pendingImports.value).toBe(0)
    expect(pairs(state.entries)).toEqual([['A', '1']])
  })

  it('is no longer pending when reading fails', async () => {
    const state = setup()
    const broken = file('.env', 'A=1')
    broken.text = () => Promise.reject(new Error('gone'))

    await state.importDroppedFiles([broken])

    expect(state.pendingImports.value).toBe(0)
  })

  it('appends to rows that are filled in', async () => {
    const state = setup([createSecretEntry({ key: 'old', value: 'x' })])

    await state.importDroppedFiles([file('prod.env', 'A=1')])

    expect(pairs(state.entries)).toEqual([
      ['old', 'x'],
      ['A', '1']
    ])
    expect(state.onSuccess).toHaveBeenCalledWith('Imported 1 key from prod.env')
  })

  it('removes every blank row, also between and after filled ones', async () => {
    const state = setup([
      createSecretEntry(),
      createSecretEntry({ key: 'old', value: 'x' }),
      createSecretEntry(),
      createSecretEntry()
    ])

    await state.importDroppedFiles([file('.env', 'A=1')])

    expect(pairs(state.entries)).toEqual([
      ['old', 'x'],
      ['A', '1']
    ])
  })

  it('leaves the rows alone if nothing could be imported', async () => {
    const state = setup([createSecretEntry(), createSecretEntry()])

    await state.importDroppedFiles([file('.env', '# nothing here')])

    expect(state.entries.value).toHaveLength(2)
  })

  it('keeps any other file as a file named after it', async () => {
    const state = setup()
    const upload = file('tls.crt', 'cert')

    await state.importDroppedFiles([upload])

    expect(state.entries.value).toHaveLength(1)
    expect(state.entries.value[0]).toMatchObject({ key: 'tls.crt', value: '', file: upload })
    expect(state.onSuccess).toHaveBeenCalledWith('Added 1 file')
  })

  it('reads plain text of KEY=VALUE lines as .env, but not base64 padding', async () => {
    const state = setup()

    await state.importDroppedFiles([
      file('settings.txt', 'MODE=prod', 'text/plain'),
      file('token.txt', 'dGVzdA==', 'text/plain')
    ])

    expect(state.entries.value.map((entry) => entry.key)).toEqual(['MODE', 'token.txt'])
    expect(state.onSuccess).toHaveBeenCalledWith(
      'Imported 1 key from settings.txt and added 1 file'
    )
  })

  it('refuses a file above the limit and says which one', async () => {
    const state = setup()

    await state.importDroppedFiles([file('big.bin', new Uint8Array(MAX_FILE_SIZE_BYTES + 1))])

    expect(state.entries.value).toHaveLength(1)
    expect(state.entries.value[0].key).toBe('')
    expect(state.onError).toHaveBeenCalledWith('big.bin: File size should be less than 1 MB!')
    expect(state.onSuccess).not.toHaveBeenCalled()
    expect(state.onImported).not.toHaveBeenCalled()
  })

  it('refuses a .env file without any pair', async () => {
    const state = setup()

    await state.importDroppedFiles([file('.env', '# nothing\n')])

    expect(state.entries.value[0].key).toBe('')
    expect(state.onError).toHaveBeenCalledWith('.env: No KEY=VALUE pairs found.')
    expect(state.onSuccess).not.toHaveBeenCalled()
  })

  it('imports what it can when some files are refused', async () => {
    const state = setup()

    await state.importDroppedFiles([file('.env', 'A=1'), file('empty.env', '')])

    expect(pairs(state.entries)).toEqual([['A', '1']])
    expect(state.onError).toHaveBeenCalledWith('empty.env: No KEY=VALUE pairs found.')
    expect(state.onSuccess).toHaveBeenCalledWith('Imported 1 key from .env')
  })
})
