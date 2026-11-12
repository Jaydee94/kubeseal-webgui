import { ref, watch } from 'vue'
import { createLogger } from '@/utils/logger'

const log = createLogger('import')

/**
 * "Import existing sealed secret": lists the SealedSecrets of the selected
 * namespace and takes over the keys of the chosen one. Entries the user
 * already typed in are only replaced after a confirmation.
 *
 * @param {object} options
 * @param {import('vue').Ref<string>} options.namespaceName the selected namespace
 * @param {import('vue').Ref<boolean>} options.enabled the feature flag
 * @param {(namespace: string) => Promise<{name: string, keys: string[]}[]>} options.fetchSealedSecrets
 * @param {() => boolean} options.hasUserEnteredData whether replacing loses input
 * @param {(keys: string[]) => void} options.applyKeys replaces the entries
 * @param {(message: string) => void} options.onError shows an error to the user
 */
export function useSealedSecretImport({
  namespaceName,
  enabled,
  fetchSealedSecrets,
  hasUserEnteredData,
  applyKeys,
  onError
}) {
  const importMenuOpen = ref(false)
  const availableSealedSecrets = ref([])
  const selectedSealedSecret = ref(null)
  const loadingSealedSecrets = ref(false)
  const confirmOverwriteDialog = ref(false)
  const pendingSealedSecret = ref(null)
  // Counts the requests that are still wanted. A response is only used if no
  // reset happened since its request: it belongs to the namespace of then.
  let currentRequest = 0

  function clearSelection() {
    availableSealedSecrets.value = []
    selectedSealedSecret.value = null
  }

  function resetSealedSecretImport() {
    currentRequest += 1
    loadingSealedSecrets.value = false
    importMenuOpen.value = false
    clearSelection()
  }

  async function loadSealedSecrets() {
    if (!namespaceName.value || !enabled.value) {
      clearSelection()
      return
    }

    const namespace = namespaceName.value
    currentRequest += 1
    const request = currentRequest
    const isStale = () => request !== currentRequest

    try {
      loadingSealedSecrets.value = true
      const sealedSecrets = await fetchSealedSecrets(namespace)
      if (isStale()) return
      availableSealedSecrets.value = sealedSecrets
    } catch (error) {
      if (isStale()) return
      log.error(`Failed to fetch existing SealedSecrets in namespace "${namespace}":`, error)
      onError(`Failed to fetch existing SealedSecrets. Error Message: ${error.message}.`)
      clearSelection()
    } finally {
      if (!isStale()) {
        loadingSealedSecrets.value = false
      }
    }
  }

  async function onImportMenuOpen() {
    if (!availableSealedSecrets.value.length) {
      await loadSealedSecrets()
    }
  }

  // The list belongs to one namespace.
  watch(namespaceName, () => {
    confirmOverwriteDialog.value = false
    pendingSealedSecret.value = null
    resetSealedSecretImport()
  })

  watch(selectedSealedSecret, (sealedSecret) => {
    if (!sealedSecret || !Array.isArray(sealedSecret.keys)) {
      return
    }
    if (hasUserEnteredData()) {
      pendingSealedSecret.value = sealedSecret
      confirmOverwriteDialog.value = true
      return
    }
    applyKeys(sealedSecret.keys)
  })

  function confirmOverwrite() {
    confirmOverwriteDialog.value = false
    if (pendingSealedSecret.value) {
      applyKeys(pendingSealedSecret.value.keys)
      pendingSealedSecret.value = null
    }
  }

  function cancelOverwrite() {
    confirmOverwriteDialog.value = false
    pendingSealedSecret.value = null
    selectedSealedSecret.value = null
  }

  return {
    importMenuOpen,
    availableSealedSecrets,
    selectedSealedSecret,
    loadingSealedSecrets,
    confirmOverwriteDialog,
    onImportMenuOpen,
    confirmOverwrite,
    cancelOverwrite,
    resetSealedSecretImport
  }
}
