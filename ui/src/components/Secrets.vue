<template>
  <div class="secrets-component">
    <v-container v-if="displayName" class="text-h5 text-gradient-primary text-center mb-2 py-0">
      {{ displayName }}
    </v-container>

    <!-- Form and Results Section -->
    <transition name="fade" mode="out-in">
      <div v-if="loading" class="d-flex justify-center align-center" style="min-height: 400px">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      </div>
      <v-card
        v-else-if="displayCreateSealedSecretForm"
        class="secrets-form modern-card pa-6 mb-6"
        elevation="1"
        variant="outlined"
      >
        <v-form autocomplete="off" @keydown="onFormKeydown">
          <SecretFormInputs
            v-model:namespace-name="namespaceName"
            v-model:secret-name="secretName"
            v-model:scope="scope"
            v-model:new-namespace="newNamespace"
            :namespaces="namespaces"
            :favorite-namespaces="favoriteNamespaces"
            @toggle-favorite="toggleFavorite"
          />

          <SecretsList
            ref="secretsList"
            :entries="secrets"
            :duplicate-keys="duplicateKeys"
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
                    color="primary"
                    size="small"
                    class="text-caption mr-1"
                    :loading="loadingSealedSecrets"
                    @click="onImportMenuOpen"
                  >
                    Import existing sealed secret
                  </v-btn>
                </template>
                <v-card>
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

          <v-row justify="center">
            <v-col cols="12" sm="8" md="6" class="d-flex flex-column align-center">
              <v-btn
                size="large"
                prepend-icon="mdi-lock"
                class="encrypt-btn px-10"
                color="primary"
                variant="elevated"
                :disabled="notReadyToEncode"
                min-width="200"
                aria-keyshortcuts="Control+Enter Meta+Enter"
                @click="seal"
              >
                Encrypt
              </v-btn>
              <!-- Not shown on touch screens, which have no such keys. -->
              <div class="shortcut-hint text-caption text-medium-emphasis mt-2" aria-hidden="true">
                or press <kbd>{{ SHORTCUT_LABEL }}</kbd>
              </div>
              <transition name="fade">
                <div
                  v-if="notReadyToEncode && !blockingError"
                  class="text-caption text-medium-emphasis text-center mt-3 d-flex align-center justify-center"
                >
                  <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
                  Please complete all required fields to encrypt
                </div>
              </transition>
            </v-col>
          </v-row>
        </v-form>
      </v-card>

      <SecretsResults
        v-else
        :sealed-secrets="sealedSecrets"
        :manifest="sealedSecretYaml"
        @copied="showClipboardMessage"
        @copy-failed="setErrorMessage"
        @clear="resetForm"
        @edit="displayCreateSealedSecretForm = true"
      />
    </transition>

    <!-- Confirmation dialog for overwriting secret keys -->
    <v-dialog v-model="confirmOverwriteDialog" max-width="440" persistent>
      <v-card>
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

    <!-- Snackbars -->
    <v-snackbar v-model="showErrorSnackbar" color="red" :timeout="ERROR_SNACKBAR_TIMEOUT_MS">
      <v-icon>mdi-alert-circle</v-icon>
      {{ errorMessage }}
    </v-snackbar>
    <v-snackbar v-model="clipboardSnackbar" color="green" :timeout="CLIPBOARD_SNACKBAR_TIMEOUT_MS">
      <v-icon>mdi-check-circle</v-icon>
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

// Configuration and data loaded from the server
const displayName = ref('')
const sealedSecretImportFeatureEnabled = ref(false)
const namespaces = ref([])

// The form
const secretName = ref('')
const namespaceName = ref('')
const scope = ref(DEFAULT_SCOPE)
const newNamespace = ref(false)
const secrets = ref([createSecretEntry()])
const secretsList = ref(null)

// Sealing and its result
const loading = ref(false)
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

const { importDroppedFiles } = useDroppedFiles({
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
    incompleteSecretData.value ||
    invalidKeyData.value ||
    duplicateKeys.value.size > 0 ||
    invalidNewNamespace.value ||
    invalidSecretName.value ||
    (scopeNeedsNamespace(scope.value) && namespaceName.value === '') ||
    (scopeNeedsName(scope.value) && secretName.value === '')
)

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
  displayName.value = config.displayName
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

function setErrorMessage(newErrorMessage) {
  errorMessage.value = newErrorMessage
  showErrorSnackbar.value = !!newErrorMessage
}

function showClipboardMessage(message) {
  clipboardMessage.value = message
  clipboardSnackbar.value = true
}

function resetForm() {
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
  if (!notReadyToEncode.value && !loading.value) seal()
}

async function seal() {
  try {
    loading.value = true
    sealedSecrets.value = await sealSecrets({
      secretName: secretName.value,
      namespaceName: namespaceName.value,
      scope: scope.value,
      entries: secrets.value
    })
    await new Promise((resolve) => setTimeout(resolve, POST_SEAL_DELAY_MS))
    displayCreateSealedSecretForm.value = false
    setErrorMessage('')
  } catch (error) {
    // Only the error is logged -- never the submitted secrets.
    log.error(
      `Failed to seal secret "${secretName.value}" in namespace "${namespaceName.value}":`,
      error
    )
    setErrorMessage(`Failed to seal secrets. Error Message: ${error.message || error}.`)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.shortcut-hint kbd {
  padding: 1px 6px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-bottom-width: 2px;
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  font-family: inherit;
  font-size: 0.85em;
  white-space: nowrap;
}

/* Touch screens have no Ctrl or Cmd key. */
@media (hover: none) {
  .shortcut-hint {
    display: none;
  }
}
</style>
