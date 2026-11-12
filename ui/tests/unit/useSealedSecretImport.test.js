import { describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { useSealedSecretImport } from '@/composables/useSealedSecretImport'
import { setLogLevel } from '@/utils/logger'

setLogLevel('silent')

const APP_SECRETS = { name: 'app-secrets', keys: ['API_KEY', 'TOKEN'] }
const DB_SECRETS = { name: 'db-secrets', keys: ['PASSWORD'] }

function setup({ userEnteredData = false, enabled = true, fetchSealedSecrets } = {}) {
  const options = {
    namespaceName: ref('team-a'),
    enabled: ref(enabled),
    fetchSealedSecrets: vi.fn(fetchSealedSecrets ?? (async () => [APP_SECRETS, DB_SECRETS])),
    hasUserEnteredData: vi.fn(() => userEnteredData),
    applyKeys: vi.fn(),
    onError: vi.fn()
  }
  return { ...options, ...useSealedSecretImport(options) }
}

describe('useSealedSecretImport', () => {
  it('loads the SealedSecrets of the namespace when the menu is opened', async () => {
    const state = setup()

    await state.onImportMenuOpen()

    expect(state.fetchSealedSecrets).toHaveBeenCalledWith('team-a')
    expect(state.availableSealedSecrets.value).toEqual([APP_SECRETS, DB_SECRETS])
    expect(state.loadingSealedSecrets.value).toBe(false)
  })

  it('does not load again while it has a list', async () => {
    const state = setup()
    await state.onImportMenuOpen()
    await state.onImportMenuOpen()
    expect(state.fetchSealedSecrets).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['the feature is disabled', { enabled: false }, 'team-a'],
    ['no namespace is selected', {}, '']
  ])('does not load when %s', async (_, options, namespace) => {
    const state = setup(options)
    state.namespaceName.value = namespace
    await nextTick()

    await state.onImportMenuOpen()

    expect(state.fetchSealedSecrets).not.toHaveBeenCalled()
    expect(state.availableSealedSecrets.value).toEqual([])
  })

  it('reports a failed request and stays empty', async () => {
    const state = setup({
      fetchSealedSecrets: async () => {
        throw new Error('HTTP 500 - nope')
      }
    })

    await state.onImportMenuOpen()

    expect(state.onError).toHaveBeenCalledWith(
      'Failed to fetch existing SealedSecrets. Error Message: HTTP 500 - nope.'
    )
    expect(state.availableSealedSecrets.value).toEqual([])
    expect(state.loadingSealedSecrets.value).toBe(false)
  })

  it('applies the keys of the selection right away when nothing was entered', async () => {
    const state = setup()

    state.selectedSealedSecret.value = APP_SECRETS
    await nextTick()

    expect(state.applyKeys).toHaveBeenCalledWith(['API_KEY', 'TOKEN'])
    expect(state.confirmOverwriteDialog.value).toBe(false)
  })

  it('asks before replacing entered data and applies on confirmation', async () => {
    const state = setup({ userEnteredData: true })

    state.selectedSealedSecret.value = APP_SECRETS
    await nextTick()
    expect(state.confirmOverwriteDialog.value).toBe(true)
    expect(state.applyKeys).not.toHaveBeenCalled()

    state.confirmOverwrite()

    expect(state.confirmOverwriteDialog.value).toBe(false)
    expect(state.applyKeys).toHaveBeenCalledExactlyOnceWith(['API_KEY', 'TOKEN'])
  })

  it('keeps the entered data when the replacement is cancelled', async () => {
    const state = setup({ userEnteredData: true })
    state.selectedSealedSecret.value = APP_SECRETS
    await nextTick()

    state.cancelOverwrite()
    await nextTick()
    state.confirmOverwrite()

    expect(state.confirmOverwriteDialog.value).toBe(false)
    expect(state.selectedSealedSecret.value).toBeNull()
    expect(state.applyKeys).not.toHaveBeenCalled()
  })

  it('ignores a selection without a key list', async () => {
    const state = setup()
    state.selectedSealedSecret.value = { name: 'broken' }
    await nextTick()
    expect(state.applyKeys).not.toHaveBeenCalled()
  })

  it('forgets list, selection and a pending confirmation when the namespace changes', async () => {
    const state = setup({ userEnteredData: true })
    await state.onImportMenuOpen()
    state.importMenuOpen.value = true
    state.selectedSealedSecret.value = APP_SECRETS
    await nextTick()

    state.namespaceName.value = 'team-b'
    await nextTick()

    expect(state.importMenuOpen.value).toBe(false)
    expect(state.availableSealedSecrets.value).toEqual([])
    expect(state.selectedSealedSecret.value).toBeNull()
    expect(state.confirmOverwriteDialog.value).toBe(false)
    state.confirmOverwrite()
    expect(state.applyKeys).not.toHaveBeenCalled()

    await state.onImportMenuOpen()
    expect(state.fetchSealedSecrets).toHaveBeenLastCalledWith('team-b')
  })

  it('resets menu, list and selection', async () => {
    const state = setup()
    await state.onImportMenuOpen()
    state.importMenuOpen.value = true

    state.resetSealedSecretImport()

    expect(state.importMenuOpen.value).toBe(false)
    expect(state.availableSealedSecrets.value).toEqual([])
    expect(state.selectedSealedSecret.value).toBeNull()
  })

  it('ignores a response that arrives after the namespace changed', async () => {
    const responses = {}
    const state = setup({
      fetchSealedSecrets: (namespace) =>
        new Promise((resolve, reject) => {
          responses[namespace] = { resolve, reject }
        })
    })

    const loadingTeamA = state.onImportMenuOpen()
    state.namespaceName.value = 'team-b'
    await nextTick()
    expect(state.loadingSealedSecrets.value).toBe(false)

    responses['team-a'].resolve([APP_SECRETS])
    await loadingTeamA
    expect(state.availableSealedSecrets.value).toEqual([])

    // the list of the new namespace is still requested and used
    const loadingTeamB = state.onImportMenuOpen()
    expect(state.fetchSealedSecrets).toHaveBeenLastCalledWith('team-b')
    responses['team-b'].resolve([DB_SECRETS])
    await loadingTeamB
    expect(state.availableSealedSecrets.value).toEqual([DB_SECRETS])
    expect(state.loadingSealedSecrets.value).toBe(false)
  })

  it('ignores a failure that arrives after the namespace changed', async () => {
    let failTeamA
    const state = setup({
      fetchSealedSecrets: () =>
        new Promise((_, reject) => {
          failTeamA = reject
        })
    })

    const loadingTeamA = state.onImportMenuOpen()
    state.namespaceName.value = 'team-b'
    await nextTick()
    failTeamA(new Error('HTTP 500 - nope'))
    await loadingTeamA

    expect(state.onError).not.toHaveBeenCalled()
  })
})
