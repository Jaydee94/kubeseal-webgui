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
              v-model:scope="scope"
              v-model:new-namespace="newNamespace"
              :namespaces="namespaces"
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
                v-if="sealedSecretImportFeatureEnabled && namespaceName && !newNamespace"
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
        :sealed-secrets="sealedSecrets"
        :manifest="sealedSecretYaml"
        :secret-name="secretName"
        :namespace="namespaceName"
        :scope="scope"
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
import { fetchNamespaces, fetchSealedSecrets, sealSecrets } from '@/api'
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
const namespaces = ref([])

// The form
const secretName = ref('')
const namespaceName = ref('')
const scope = ref(DEFAULT_SCOPE)
const newNamespace = ref(false)
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
// What could not be loaded at start-up: '', 'config' or 'namespaces'. Unlike
// the error message this does not go away, because nothing retries the load.
const loadError = ref('')
const displayCreateSealedSecretForm = ref(true)
const sealedSecrets = ref([])

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

const invalidNewNamespace = computed(
  () => newNamespace.value && scopeNeedsNamespace(scope.value) && !isDnsLabel(namespaceName.value)
)

// Only a failed load blocks sealing; a failed attempt to seal or to copy can
// simply be repeated. Failing to list the cluster's namespaces only affects
// the dropdown, so it blocks neither a manually entered namespace nor a scope
// that needs no namespace.
const blockingError = computed(
  () =>
    loadError.value === 'config' ||
    (loadError.value === 'namespaces' && scopeNeedsNamespace(scope.value) && !newNamespace.value)
)

// A secret name is optional outside the strict scope, but a name that is not
// a valid DNS subdomain would end up as broken YAML in the result.
const invalidSecretName = computed(() => !!secretName.value && !isDnsSubdomain(secretName.value))

const notReadyToEncode = computed(
  () =>
    blockingError.value ||
    pendingImports.value > 0 ||
    incompleteSecretData.value ||
    invalidKeyData.value ||
    duplicateKeys.value.size > 0 ||
    invalidNewNamespace.value ||
    invalidSecretName.value ||
    (scopeNeedsNamespace(scope.value) && namespaceName.value === '') ||
    (scopeNeedsName(scope.value) && secretName.value === '')
)

// What Encrypt is about to seal, e.g. "2 keys · payments · strict".
const readySummary = computed(() => {
  const count = secrets.value.length
  const parts = [`${count} ${count === 1 ? 'key' : 'keys'}`]
  if (scopeNeedsNamespace(scope.value) && namespaceName.value) parts.push(namespaceName.value)
  parts.push(scope.value)
  return parts.join(' · ')
})

const sealStatus = computed(() => {
  if (!displayCreateSealedSecretForm.value) return 'Sealed secret ready.'
  return sealing.value ? 'Sealing…' : ''
})

const sealedSecretYaml = computed(() =>
  renderSealedSecretYaml({
    name: secretName.value,
    namespace: namespaceName.value,
    scope: scope.value,
    entries: sealedSecrets.value
  })
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
  await loadNamespaces()
})

// A value picked from the cluster list is not valid as free text and vice
// versa, so start from an empty field whenever the mode changes.
watch(newNamespace, () => {
  namespaceName.value = ''
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

function resetForm() {
  focusAfterSwap = 'form'
  displayCreateSealedSecretForm.value = true
  secretName.value = ''
  namespaceName.value = ''
  newNamespace.value = false
  scope.value = DEFAULT_SCOPE
  secrets.value = [createSecretEntry()]
  sealedSecrets.value = []
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
  try {
    sealedSecrets.value = await sealSecrets({
      secretName: secretName.value,
      namespaceName: namespaceName.value,
      scope: scope.value,
      entries: secrets.value
    })
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
      `Failed to seal secret "${secretName.value}" in namespace "${namespaceName.value}":`,
      error
    )
    setErrorMessage(`Failed to seal secrets. Error Message: ${error.message || error}.`)
    sealing.value = false
    sealed.value = false
    await restoreFocus()
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
