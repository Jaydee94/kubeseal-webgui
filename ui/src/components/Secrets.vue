<template>
  <div class="secrets-component">
    <!-- Outside the inert form, so that it is announced while sealing. -->
    <div class="seal-status d-sr-only" aria-live="polite">{{ sealStatus }}</div>

    <!-- Form and Results Section. The form stays on screen while sealing (its
         button shows the progress), so there is never an empty page. -->
    <transition name="swap" mode="out-in" appear @after-enter="onSwapEntered">
      <div v-if="displayCreateSealedSecretForm" class="secrets-form">
        <!-- Inert while sealing: what is edited now would not be sealed. -->
        <v-form
          ref="form"
          autocomplete="off"
          class="secrets-form__panels"
          :inert="sealing"
          @keydown="onFormKeydown"
        >
          <!-- Where the secret goes: scope, namespace and name. -->
          <section class="panel form-panel" aria-label="Target">
            <SecretFormInputs
              ref="formInputs"
              v-model:namespace-name="namespaceName"
              v-model:secret-name="secretName"
              v-model:cluster="selectedCluster"
              v-model:additional-namespaces="additionalNamespaces"
              :clusters="clusters"
              :scope="scope"
              v-model:new-namespace="newNamespace"
              @update:scope="pickScope"
              :namespaces="namespaces"
              :namespace-listing="namespaceListingActive"
              :favorite-namespaces="favoriteNamespaces"
              @toggle-favorite="toggleFavorite"
            />
          </section>

          <!-- What goes into it: the key/value pairs. -->
          <section class="panel form-panel" aria-labelledby="pairsTitle">
            <SecretsList
              ref="secretsList"
              :entries="secrets"
              :duplicate-keys="duplicateKeys"
              :importing="pendingImports > 0"
              @update-entry="updateEntry"
              @select-file="selectFile"
              @add-entry="addEntry"
              @remove-entry="removeEntry"
              @remove-all="removeAllEntries"
              @drop-files="importDroppedFiles"
            >
              <template
                v-if="sealedSecretImportFeatureEnabled && existingNamespaceEntered"
                #header-actions
              >
                <v-menu
                  v-model="importMenuOpen"
                  :close-on-content-click="false"
                  location="bottom end"
                  min-width="280"
                >
                  <template #activator="{ props: menuProps }">
                    <v-btn
                      v-bind="menuProps"
                      prepend-icon="mdi-import"
                      variant="text"
                      size="small"
                      class="btn-ghost result-action"
                      :loading="loadingSealedSecrets"
                      @click="onImportMenuOpen"
                    >
                      Import existing sealed secret
                    </v-btn>
                  </template>
                  <v-card class="panel">
                    <v-card-text class="pa-3">
                      <v-autocomplete
                        v-model="selectedSealedSecret"
                        :items="availableSealedSecrets"
                        item-title="name"
                        return-object
                        label="Select SealedSecret"
                        autocomplete="off"
                        variant="outlined"
                        density="compact"
                        color="primary"
                        class="modern-input"
                        no-data-text="No SealedSecrets found"
                        :loading="loadingSealedSecrets"
                        auto-select-first
                        @update:model-value="importMenuOpen = false"
                      />
                    </v-card-text>
                  </v-card>
                </v-menu>
              </template>
            </SecretsList>
          </section>

          <!-- The one primary action, at the end of the form. -->
          <div class="panel action-bar">
            <div class="action-bar__status text-body-2">
              <transition name="fade" mode="out-in">
                <div
                  v-if="notReadyToEncode && !blockingError"
                  key="incomplete"
                  class="d-flex align-center text-medium-emphasis"
                >
                  <v-icon size="small" class="mr-2">mdi-information-outline</v-icon>
                  Please complete all required fields to encrypt
                </div>
                <div v-else-if="!blockingError" key="ready" class="d-flex align-center">
                  <span class="ready-dot mr-2" aria-hidden="true" />
                  Ready to seal
                  <span class="meta ml-2">{{ readySummary }}</span>
                </div>
              </transition>
            </div>
            <div class="action-bar__submit">
              <!-- Not shown on touch screens, which have no such keys. -->
              <span class="shortcut-hint text-caption text-medium-emphasis" aria-hidden="true">
                <kbd>{{ SHORTCUT_LABEL }}</kbd>
              </span>
              <v-btn
                ref="encryptButton"
                class="encrypt-btn px-6"
                :class="{ 'encrypt-btn--sealing': sealing }"
                color="primary"
                variant="flat"
                :disabled="notReadyToEncode || sealing"
                :aria-busy="sealing"
                min-width="160"
                aria-keyshortcuts="Control+Enter Meta+Enter"
                @click="seal"
              >
                <template #prepend>
                  <!-- The lock is open until the secret is sealed, then it
                       snaps shut while the result is about to show. -->
                  <v-icon
                    :icon="sealed ? 'mdi-lock' : 'mdi-lock-open-variant'"
                    :class="{ 'lock-snap': sealed }"
                  />
                </template>
                {{ sealing ? 'Sealing…' : 'Encrypt' }}
              </v-btn>
            </div>
          </div>
        </v-form>
      </div>

      <SecretsResults
        v-else
        :results="sealedResults"
        :secret-name="secretName"
        :scope="scope"
        :cluster="sealedForCluster"
        @copied="showClipboardMessage"
        @downloaded="showClipboardMessage"
        @copy-failed="setErrorMessage"
        @clear="resetForm"
        @edit="editSecrets"
      />
    </transition>

    <!-- Confirmation dialog for overwriting secret keys -->
    <v-dialog v-model="confirmOverwriteDialog" max-width="440" persistent>
      <v-card class="panel pa-2">
        <v-card-title class="text-h6">Replace key list?</v-card-title>
        <v-card-text>
          This will replace the current key-value list with keys from the selected SealedSecret.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="cancelOverwrite">Cancel</v-btn>
          <v-btn color="primary" variant="elevated" @click="confirmOverwrite">Continue</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbars: at the top, because the actions of the result view are at
         the bottom of the page and must stay clickable. -->
    <v-snackbar
      v-model="showErrorSnackbar"
      color="error"
      location="top"
      class="toast"
      :timeout="ERROR_SNACKBAR_TIMEOUT_MS"
    >
      <v-icon class="mr-2">mdi-alert-circle</v-icon>
      {{ errorMessage }}
    </v-snackbar>
    <v-snackbar
      v-model="clipboardSnackbar"
      color="success"
      location="top"
      class="toast"
      :timeout="CLIPBOARD_SNACKBAR_TIMEOUT_MS"
    >
      <v-icon class="mr-2">mdi-check-circle</v-icon>
      {{ clipboardMessage }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onBeforeMount, watch } from 'vue'
import SecretFormInputs from './SecretFormInputs.vue'
import SecretsList from './SecretsList.vue'
import SecretsResults from './SecretsResults.vue'
import { fetchClusters, fetchNamespaces, fetchSealedSecrets, sealSecrets } from '@/api'
import { loadConfig } from '@/config'
import { useFavoriteNamespaces } from '@/composables/useFavoriteNamespaces'
import { useDroppedFiles } from '@/composables/useDroppedFiles'
import { useFileDropGuard } from '@/composables/useFileDropGuard'
import { useSealedSecretImport } from '@/composables/useSealedSecretImport'
import {
  CLIPBOARD_SNACKBAR_TIMEOUT_MS,
  DEFAULT_SCOPE,
  ERROR_SNACKBAR_TIMEOUT_MS,
  FILE_TOO_LARGE_MESSAGE,
  POST_SEAL_DELAY_MS,
  scopeNeedsName,
  scopeNeedsNamespace
} from '@/constants'
import { createLogger } from '@/utils/logger'
import { mapWithLimit } from '@/utils/concurrency'
import { firstInvalidNamespace, namespacesToSeal } from '@/utils/namespaces'
import { renderSealedSecretYaml } from '@/utils/sealedSecretYaml'
import {
  createSecretEntry,
  findDuplicateKeys,
  isEntryBlank,
  isEntryComplete
} from '@/utils/secretEntry'
import {
  firstRuleMessage,
  isDnsLabel,
  isDnsSubdomain,
  isFileTooLarge,
  rules
} from '@/utils/validation'

defineOptions({
  name: 'SecretsManager'
})

const log = createLogger('Secrets')

// Sealing requests sent at the same time for several namespaces.
const PARALLEL_SEALING_REQUESTS = 4

// Mac users know the command key, everyone else Ctrl.
const SHORTCUT_LABEL = /Mac|iPhone|iPad/i.test(
  navigator.userAgentData?.platform ?? navigator.platform ?? ''
)
  ? '⌘ Enter'
  : 'Ctrl Enter'
const { favoriteNamespaces, toggleFavorite } = useFavoriteNamespaces()

// Configuration and data loaded from the server (the display name is shown
// in the header, see App.vue)
const sealedSecretImportFeatureEnabled = ref(false)
// Off where the API may not list the namespaces of the cluster: the namespace
// is typed in then.
const namespaceListingEnabled = ref(true)
const namespaces = ref([])
// The clusters to seal for, and the one picked. Empty for an API that does not
// know them: it has one cluster, and nothing is sent about it.
const clusters = ref([])
const selectedCluster = ref('')
// Only while GET /clusters is answered (only with several clusters).
const clustersLoading = ref(false)
// GET /clusters has answered.
const clustersKnown = ref(false)
// The scope of a new form, from config.json.
const defaultScope = ref(DEFAULT_SCOPE)
// The form can be used while config.json loads: a scope the user picked
// meanwhile is not replaced by the configured default, even if it is the
// built-in one again.
let scopePickedByUser = false

// The form
const secretName = ref('')
const namespaceName = ref('')
const scope = ref(DEFAULT_SCOPE)
const newNamespace = ref(false)
// More namespaces to seal the same secret for, next to the main one.
const additionalNamespaces = ref([])
const secrets = ref([createSecretEntry()])
const secretsList = ref(null)
const form = ref(null)
const formInputs = ref(null)

// Sealing and its result
// From the click on Encrypt until the form is shown again, or the sealing failed.
const sealing = ref(false)
// The secret is sealed and the result is about to show.
const sealed = ref(false)
const encryptButton = ref(null)
// What could not be loaded at start-up: '', 'config', 'clusters' or
// 'namespaces'. Unlike
// the error message this does not go away, because nothing retries the load.
const loadError = ref('')
const displayCreateSealedSecretForm = ref(true)
// What was sealed, one entry per namespace: [{ namespace, entries }, ...].
const sealedByNamespace = ref([])
// The cluster that sealed them, shown in the result. Empty for a single cluster.
const sealedForCluster = ref('')

// Feedback
const errorMessage = ref('')
const showErrorSnackbar = ref(false)
const clipboardSnackbar = ref(false)
const clipboardMessage = ref('')

const {
  importMenuOpen,
  availableSealedSecrets,
  selectedSealedSecret,
  loadingSealedSecrets,
  confirmOverwriteDialog,
  onImportMenuOpen,
  confirmOverwrite,
  cancelOverwrite,
  resetSealedSecretImport
} = useSealedSecretImport({
  namespaceName,
  enabled: sealedSecretImportFeatureEnabled,
  fetchSealedSecrets,
  hasUserEnteredData: () => secrets.value.some((entry) => !isEntryBlank(entry)),
  applyKeys: replaceEntriesWithKeys,
  onError: setErrorMessage
})

const { importDroppedFiles, pendingImports } = useDroppedFiles({
  entries: secrets,
  onSuccess: showClipboardMessage,
  onError: setErrorMessage,
  onImported: showInvalidKeys
})

// A file dropped next to the list must not replace the page.
useFileDropGuard('.secrets-list')

const incompleteSecretData = computed(() => secrets.value.some((entry) => !isEntryComplete(entry)))

// The key field shows the reason, so a key like "my file.txt" (from a dropped
// file) must not be sealed as if nothing were wrong.
const invalidKeyData = computed(() =>
  secrets.value.some(
    (entry) => entry.key !== '' && firstRuleMessage(rules.validSecretKey, entry.key) !== ''
  )
)

// Two rows with the same key would end up as a duplicated key in the YAML.
const duplicateKeys = computed(() => findDuplicateKeys(secrets.value))

// The API can only list namespaces and read SealedSecrets of the cluster it
// runs in. For any other cluster the namespace is typed in, whatever
// enableNamespaceListing says. Without a cluster list there is one cluster,
// and it is that one.
const inOwnCluster = computed(
  () => clusters.value.find((entry) => entry.name === selectedCluster.value)?.inCluster ?? true
)
const namespaceListingActive = computed(() => namespaceListingEnabled.value && inOwnCluster.value)

// A typed-in namespace: a new one, or any one without the cluster's list.
const freeTextNamespace = computed(() => newNamespace.value || !namespaceListingActive.value)

const invalidFreeTextNamespace = computed(
  () =>
    freeTextNamespace.value && scopeNeedsNamespace(scope.value) && !isDnsLabel(namespaceName.value)
)

// Every namespace the secret is sealed for. A cluster-wide secret has none of
// its own.
const targetNamespaces = computed(() =>
  scopeNeedsNamespace(scope.value)
    ? namespacesToSeal(namespaceName.value, additionalNamespaces.value)
    : [namespaceName.value]
)

// Typed-in names are checked, those of the list are valid by being in it.
const invalidAdditionalNamespace = computed(
  () =>
    freeTextNamespace.value &&
    scopeNeedsNamespace(scope.value) &&
    firstInvalidNamespace(additionalNamespaces.value) !== ''
)

// A namespace that may hold SealedSecrets to import from: one of the list, or
// a valid name typed in without the list (not one that does not exist yet).
const existingNamespaceEntered = computed(
  () =>
    inOwnCluster.value &&
    !!namespaceName.value &&
    !newNamespace.value &&
    !invalidFreeTextNamespace.value
)

// Only a failed load blocks sealing; a failed attempt to seal or to copy can
// simply be repeated. Failing to list the cluster's namespaces only affects
// the dropdown, so it blocks neither a manually entered namespace nor a scope
// that needs no namespace.
const blockingError = computed(
  () =>
    loadError.value === 'config' ||
    loadError.value === 'clusters' ||
    (loadError.value === 'namespaces' &&
      namespaceListingActive.value &&
      scopeNeedsNamespace(scope.value) &&
      !newNamespace.value)
)

// A secret name is optional outside the strict scope, but a name that is not
// a valid DNS subdomain would end up as broken YAML in the result.
const invalidSecretName = computed(() => !!secretName.value && !isDnsSubdomain(secretName.value))

const notReadyToEncode = computed(
  () =>
    blockingError.value ||
    clustersLoading.value ||
    pendingImports.value > 0 ||
    incompleteSecretData.value ||
    invalidKeyData.value ||
    duplicateKeys.value.size > 0 ||
    invalidFreeTextNamespace.value ||
    invalidAdditionalNamespace.value ||
    invalidSecretName.value ||
    (scopeNeedsNamespace(scope.value) && namespaceName.value === '') ||
    (scopeNeedsName(scope.value) && secretName.value === '')
)

// What Encrypt is about to seal, e.g. "2 keys · payments · strict".
const readySummary = computed(() => {
  const count = secrets.value.length
  const parts = [`${count} ${count === 1 ? 'key' : 'keys'}`]
  if (clusters.value.length > 1) parts.push(selectedCluster.value)
  if (scopeNeedsNamespace(scope.value) && namespaceName.value) {
    const namespaceCount = targetNamespaces.value.length
    parts.push(namespaceCount > 1 ? `${namespaceCount} namespaces` : namespaceName.value)
  }
  parts.push(scope.value)
  return parts.join(' · ')
})

const sealStatus = computed(() => {
  if (!displayCreateSealedSecretForm.value) return 'Sealed secret ready.'
  return sealing.value ? 'Sealing…' : ''
})

const sealedResults = computed(() =>
  sealedByNamespace.value.map(({ namespace, entries }) => ({
    namespace,
    entries,
    manifest: renderSealedSecretYaml({
      name: secretName.value,
      namespace,
      scope: scope.value,
      entries
    })
  }))
)

onBeforeMount(async () => {
  let config
  try {
    config = await loadConfig()
  } catch (error) {
    log.error('Failed to load the UI configuration (config.json):', error)
    loadError.value = 'config'
    setErrorMessage(`Failed to load the UI configuration. Error Message: ${error.message}.`)
    return
  }
  sealedSecretImportFeatureEnabled.value = config.importEnabled
  namespaceListingEnabled.value = config.namespaceListingEnabled
  defaultScope.value = config.defaultScope
  if (!scopePickedByUser) {
    scope.value = config.defaultScope
  }
  // Only with several clusters: an installation with one cluster makes no
  // request it did not make before.
  if (config.multipleClusters) {
    await loadClusters()
    if (loadError.value === 'clusters') return
  }
  // Without the list nothing is requested, so no error is shown either. Nor
  // when none of the clusters is the one of the API.
  if (config.namespaceListingEnabled && inOwnClusterConfigured()) {
    await loadNamespaces()
  }
})

function inOwnClusterConfigured() {
  return clusters.value.length === 0 || clusters.value.some((entry) => entry.inCluster)
}

async function loadClusters() {
  // Until the clusters are known, sealing would go to the API's first one,
  // whichever the user meant to pick.
  clustersLoading.value = true
  try {
    clusters.value = await fetchClusters()
    clustersKnown.value = true
  } catch (error) {
    // Several clusters are configured, but not which: sealing now would use
    // the API's first one without the user seeing it, and a certificate of
    // the wrong cluster seals without an error. So it is blocked.
    clusters.value = []
    log.error('Failed to fetch the clusters:', error)
    loadError.value = 'clusters'
    setErrorMessage(
      `Failed to fetch the clusters, so it is unknown which certificate would seal. Error Message: ${error.message}.`
    )
  } finally {
    clustersLoading.value = false
  }
  selectedCluster.value = clusters.value[0]?.name ?? ''
}

// A value picked from the cluster list is not valid as free text and vice
// versa, so start from an empty field whenever the mode changes.
watch(newNamespace, () => {
  namespaceName.value = ''
  additionalNamespaces.value = []
})

// Switching between the cluster of the API (a list) and another one (typed in)
// changes the mode of the field, like the checkbox above. Only a real change
// of the mode clears it: a name typed in as a new namespace is still typed in
// when the namespaces turn out not to be listed (e.g. while config.json loads).
watch(freeTextNamespace, () => {
  namespaceName.value = ''
  additionalNamespaces.value = []
})

// The namespace is irrelevant for cluster-wide secrets.
watch(scope, (newScope) => {
  if (!scopeNeedsNamespace(newScope)) {
    newNamespace.value = false
  }
})

async function loadNamespaces() {
  try {
    namespaces.value = await fetchNamespaces()
  } catch (error) {
    log.error('Failed to fetch namespaces:', error)
    loadError.value = 'namespaces'
    setErrorMessage(`Failed to fetch namespaces. Error Message: ${error.message}.`)
  }
}

// Both snackbars sit at the same place, so they would be drawn over each
// other (a drop of a good and a too large file reports both). The error wins:
// it is what the user has to act on, while the success is visible anyway, as
// the new rows, the copied button or the download.
function setErrorMessage(newErrorMessage) {
  errorMessage.value = newErrorMessage
  showErrorSnackbar.value = !!newErrorMessage
  if (newErrorMessage) clipboardSnackbar.value = false
}

function showClipboardMessage(message) {
  if (showErrorSnackbar.value) return
  clipboardMessage.value = message
  clipboardSnackbar.value = true
}

function pickScope(newScope) {
  scopePickedByUser = true
  scope.value = newScope
}

function resetForm() {
  focusAfterSwap = 'form'
  displayCreateSealedSecretForm.value = true
  secretName.value = ''
  namespaceName.value = ''
  additionalNamespaces.value = []
  newNamespace.value = false
  scope.value = defaultScope.value
  secrets.value = [createSecretEntry()]
  sealedByNamespace.value = []
  resetSealedSecretImport()
  setErrorMessage('')
}

// Back to the filled form to change something.
function editSecrets() {
  focusAfterSwap = 'form'
  displayCreateSealedSecretForm.value = true
}

// The view that is swapped out takes the focus with it (the clicked button, or
// the form that went inert), which would leave keyboard and screen reader users
// at the top of the page. What to focus is decided by the action that swaps,
// so that the first appearance of the form at page load does not grab it.
let focusAfterSwap = null

function onSwapEntered(element) {
  const target = focusAfterSwap
  focusAfterSwap = null
  if (target === 'results') {
    // The title names the new view; the actions follow it in the tab order.
    element.querySelector('.result-card__title')?.focus()
  } else if (target === 'form') {
    // The first field, not the Encrypt button at the end of a possibly long
    // form. The namespace is disabled for a cluster-wide secret.
    element.querySelector('#namespaceSelection:not(:disabled), #secretName')?.focus()
  }
}

// A new pair is meant to be typed into right away.
async function addEntry() {
  const entry = createSecretEntry()
  secrets.value.push(entry)
  await nextTick()
  secretsList.value?.focusKey(entry.id)
}

// A dropped file is named by its file name, which is often not a valid key
// ("my file.txt"). The key is not changed, but its error is shown right away
// instead of after a visit, so it is clear why Encrypt is disabled.
async function showInvalidKeys(imported) {
  await nextTick()
  for (const entry of imported) {
    if (firstRuleMessage(rules.validSecretKey, entry.key) !== '') {
      secretsList.value?.validateKey(entry.id)
    }
  }
}

function findEntry(id) {
  return secrets.value.find((entry) => entry.id === id)
}

function updateEntry(id, changes) {
  const entry = findEntry(id)
  Object.assign(entry, changes)
  // A text value replaces the file, and with it the error of a rejected one.
  if (changes.value) {
    entry.fileError = ''
  }
}

// A file above the size limit is rejected right away instead of being kept
// in the form with an error.
function selectFile(id, file) {
  const entry = findEntry(id)
  if (!file) {
    entry.file = null
    return
  }
  if (isFileTooLarge(file)) {
    entry.file = null
    entry.fileError = FILE_TOO_LARGE_MESSAGE
    setErrorMessage(FILE_TOO_LARGE_MESSAGE)
    return
  }
  entry.file = file
  entry.fileError = ''
  setErrorMessage('')
}

// The list never becomes empty: removing the only row leaves a blank one.
function removeEntry(id) {
  const remaining = secrets.value.filter((entry) => entry.id !== id)
  secrets.value = remaining.length > 0 ? remaining : [createSecretEntry()]
}

function removeAllEntries() {
  secrets.value = [createSecretEntry()]
}

function replaceEntriesWithKeys(keys) {
  const entries = keys.map((key) => createSecretEntry({ key }))
  secrets.value = entries.length > 0 ? entries : [createSecretEntry()]
}

// Ctrl/Cmd+Enter seals from anywhere in the form. Plain Enter is left alone:
// it must still add a line in the value, and it selects in the lists.
function onFormKeydown(event) {
  if (event.key !== 'Enter' || !(event.ctrlKey || event.metaKey) || event.isComposing) return
  event.preventDefault()
  seal()
}

// Encrypt is disabled for a form that is not ready, but the shortcut has no
// such visible hint: it shows what is missing instead of doing nothing.
async function revealErrors() {
  // Fields with rules (keys, the name of a new namespace)...
  await form.value?.validate()
  // ...and the ones that check themselves only once visited.
  formInputs.value?.showErrors()
  await nextTick()
  // (The autocomplete has a hidden input of its own, which cannot be focused.)
  document
    .querySelector(
      '.secrets-form .v-input--error input:not([type="hidden"]), .secrets-form .v-input--error textarea'
    )
    ?.focus()
}

// Both ways in (button and shortcut) end up here, so this is where double
// submits and a form that is not ready are stopped.
async function seal() {
  // A dropped file that is still being read is not in the list yet; the
  // shortcut must not seal without it, nor flag fields that are about to fill.
  if (sealing.value || pendingImports.value > 0) return
  if (notReadyToEncode.value) {
    await revealErrors()
    return
  }
  sealing.value = true
  // The form can be filled in while config.json loads. With several clusters
  // nothing is sent before they are known: the user has not seen which one
  // the secret would be sealed for. (With one cluster this seals as before.)
  // A failed config.json stops it too: sealSecrets() would ask again, and a
  // retry that succeeds could seal for several clusters without one. The
  // failure itself is reported, and blocks the form, at start-up.
  let config
  try {
    config = await loadConfig()
  } catch {
    config = null
  }
  if (!config || (config.multipleClusters && !clustersKnown.value)) {
    sealing.value = false
    await restoreFocus()
    return
  }
  try {
    // One request per namespace: it is part of what a value is sealed for.
    // A few at a time, so that a long list neither floods the API with
    // kubeseal processes nor keeps going after one failed. The result shows
    // only when all of them succeeded, so that a namespace is never silently
    // missing from it.
    sealedByNamespace.value = await mapWithLimit(
      targetNamespaces.value,
      PARALLEL_SEALING_REQUESTS,
      sealForNamespace
    )
    sealedForCluster.value = clusters.value.length > 1 ? selectedCluster.value : ''
    sealed.value = true
    await new Promise((resolve) => setTimeout(resolve, POST_SEAL_DELAY_MS))
    // `sealing` stays on until the form is back (see the watcher), so that the
    // button does not turn back into "Encrypt" while the form fades out.
    focusAfterSwap = 'results'
    displayCreateSealedSecretForm.value = false
    setErrorMessage('')
  } catch (error) {
    // Only the error is logged -- never the submitted secrets.
    log.error(
      `Failed to seal secret "${secretName.value}" in namespace "${error.namespace ?? namespaceName.value}"` +
        (selectedCluster.value ? ` of cluster "${selectedCluster.value}":` : ':'),
      error
    )
    // With several namespaces, say which one failed.
    const where = error.namespace ? ` for namespace "${error.namespace}"` : ''
    setErrorMessage(`Failed to seal secrets${where}. Error Message: ${error.message || error}.`)
    sealing.value = false
    sealed.value = false
    await restoreFocus()
  }
}

async function sealForNamespace(namespace) {
  try {
    const entries = await sealSecrets({
      secretName: secretName.value,
      namespaceName: namespace,
      scope: scope.value,
      entries: secrets.value,
      cluster: selectedCluster.value
    })
    return { namespace, entries }
  } catch (error) {
    // Only for several namespaces: a single one needs no pointer to itself.
    if (targetNamespaces.value.length > 1 && error && typeof error === 'object') {
      error.namespace = namespace
    }
    throw error
  }
}

// The inert form dropped the focus; the user presses Encrypt again next.
async function restoreFocus() {
  await nextTick()
  if (document.activeElement === document.body) {
    encryptButton.value?.$el.focus()
  }
}

watch(displayCreateSealedSecretForm, (displayed) => {
  if (displayed) {
    sealing.value = false
    sealed.value = false
  }
})
</script>

<style scoped>
.secrets-form__panels {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-panel {
  padding: 20px 24px 24px;
}

/* Status on the left, the action on the right, like a toolbar. */
.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  padding: 12px 12px 12px 24px;
}

.action-bar__status {
  min-width: 0;
  min-height: 24px;
}

.action-bar__submit {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.ready-dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgb(var(--v-theme-success));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-success), 0.18);
}

/* Touch screens have no Ctrl or Cmd key. */
@media (hover: none) {
  .shortcut-hint {
    display: none;
  }
}

@media (max-width: 599px) {
  .form-panel {
    padding: 16px;
  }

  .action-bar {
    padding: 12px 16px;
  }

  /* On a phone the button spans the bar: an easy target for a thumb. */
  .action-bar__submit,
  .action-bar__submit .encrypt-btn {
    flex: 1 1 100%;
  }
}
</style>
