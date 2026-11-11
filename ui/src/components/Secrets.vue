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
        <v-form autocomplete="off">
          <SecretFormInputs
            v-model:namespace-name="namespaceName"
            v-model:secret-name="secretName"
            v-model:scope="scope"
            v-model:new-namespace="newNamespace"
            :namespaces="namespaces"
            :rules="rules"
            :secret-name-error="secretNameError"
            :favorite-namespaces="favoriteNamespaces"
            @toggle-favorite="toggleFavorite"
          />

          <SecretsList
            :entries="secrets"
            :rules="rules"
            @update-entry="updateEntry"
            @select-file="selectFile"
            @add-entry="secrets.push(createSecretEntry())"
            @remove-entry="removeEntry"
            @remove-all="removeAllEntries"
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
                @click="fetchEncodedSecrets()"
              >
                Encrypt
              </v-btn>
              <transition name="fade">
                <div
                  v-if="notReadyToEncode && !hasErrorMessage"
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
        ref="secretsResultsRef"
        :sealed-secrets="sealedSecrets"
        :secret-name="secretName"
        :namespace-name="namespaceName"
        :sealed-secrets-annotations="sealedSecretsAnnotations"
        :rendered-secrets="renderedSecrets"
        :clipboard-available="clipboardAvailable"
        :copied-individual="copiedIndividual"
        :is-copied-main="isCopiedMain"
        @copy-main="copyRenderedSecrets"
        @copy-individual="copySealedSecret"
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
import { ref, computed, onBeforeMount, onMounted, watch } from 'vue'
import SecretFormInputs from './SecretFormInputs.vue'
import SecretsList from './SecretsList.vue'
import SecretsResults from './SecretsResults.vue'
import { useConfig } from '@/composables/useConfig'
import { createLogger } from '@/utils/logger'
import { useSecrets } from '@/composables/useSecrets'
import {
  CLIPBOARD_SNACKBAR_TIMEOUT_MS,
  COPIED_FEEDBACK_MS,
  DEFAULT_SCOPE,
  ERROR_SNACKBAR_TIMEOUT_MS,
  FILE_TOO_LARGE_MESSAGE,
  MAX_FILE_SIZE_BYTES,
  POST_SEAL_DELAY_MS,
  SCOPE_STRICT,
  scopeNeedsName,
  scopeNeedsNamespace
} from '@/constants'
import { createSecretEntry, isEntryBlank, isEntryComplete } from '@/utils/secretEntry'

defineOptions({
  name: 'SecretsManager'
})

const { fetchConfig } = useConfig()
const log = createLogger('Secrets')
const {
  fetchNamespaces,
  fetchSealedSecrets,
  fetchEncodedSecrets: fetchEncodedSecretsApi
} = useSecrets()

const config = ref({})
const namespaces = ref([])
const errorMessage = ref('')
const hasErrorMessage = ref(false)
const errorSource = ref('')
const displayName = ref('')
const displayCreateSealedSecretForm = ref(true)
const loading = ref(false)
const secretName = ref('')
const namespaceName = ref('')
const scope = ref(DEFAULT_SCOPE)
const newNamespace = ref(false)
const secrets = ref([createSecretEntry()])
const sealedSecrets = ref([])
const secretsResultsRef = ref()
const clipboardAvailable = ref(false)
const favoriteNamespaces = ref(readFavoriteNamespaces())
const showErrorSnackbar = ref(false)
const clipboardSnackbar = ref(false)
const clipboardMessage = ref('')
const isCopiedMain = ref(false)
const copiedIndividual = ref({})
const sealedSecretImportFeatureEnabled = ref(false)
const importMenuOpen = ref(false)
const availableSealedSecrets = ref([])
const selectedSealedSecret = ref(null)
const loadingSealedSecrets = ref(false)
const confirmOverwriteDialog = ref(false)
const pendingNewSealedSecret = ref(null)
const secretNameError = computed(() => {
  // The name is only sealed into the secret for the strict scope.
  if (scopeNeedsName(scope.value) && !secretName.value) return 'Secret name is required.'
  return ''
})

const resetForm = () => {
  displayCreateSealedSecretForm.value = true
  secretName.value = ''
  namespaceName.value = ''
  newNamespace.value = false
  scope.value = DEFAULT_SCOPE
  secrets.value = [createSecretEntry()]
  sealedSecrets.value = []
  resetSealedSecretImport()
  hasErrorMessage.value = false
  errorSource.value = ''
  errorMessage.value = ''
}

onBeforeMount(async () => {
  try {
    config.value = await fetchConfig()
  } catch (error) {
    log.error('Failed to load the UI configuration (config.json):', error)
    setErrorMessage(`Failed to load the UI configuration. Error Message: ${error.message}.`)
    return
  }
  sealedSecretImportFeatureEnabled.value = isEnabled(
    config.value.enable_existing_sealed_secret_loading
  )
  await fetchNamespacesData(config.value)
  await fetchDisplayName(config.value)
})

onMounted(() => {
  // Copy is considered available when either the async Clipboard API is
  // present (secure contexts / HTTPS / localhost) or the legacy
  // execCommand fallback can be used. The latter ensures the copy buttons
  // remain visible when the app is served over plain HTTP, where
  // navigator.clipboard is undefined.
  clipboardAvailable.value = isClipboardSupported()
  setErrorMessage('')
})

function isClipboardSupported() {
  if (navigator && navigator.clipboard) {
    return true
  }
  return typeof document !== 'undefined' && typeof document.execCommand === 'function'
}

async function copyToClipboard(text) {
  // Prefer the modern asynchronous Clipboard API when available in a
  // secure context.
  if (navigator && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (error) {
      log.warn('Clipboard API failed, falling back to execCommand:', error)
      // Fall through to the legacy fallback below.
    }
  }

  // Fallback for non-secure contexts (e.g. served over plain HTTP) where
  // navigator.clipboard is unavailable.
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '-9999px'
    textarea.style.left = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    if (!successful) {
      log.warn('Copying to the clipboard via execCommand was rejected.')
    }
    return successful
  } catch (error) {
    log.error('Copying to the clipboard failed:', error)
    return false
  }
}

function readFavoriteNamespaces() {
  try {
    if (localStorage.favoriteNamespaces === undefined) {
      return new Set([])
    }
    return new Set(JSON.parse(localStorage.favoriteNamespaces))
  } catch (error) {
    log.warn('Ignoring unreadable favorite namespaces in localStorage:', error)
    return new Set([])
  }
}

function isEnabled(value) {
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'string') {
    return ['true', '1', 'yes', 'on'].includes(value.toLowerCase())
  }
  return false
}

function validDnsSubdomain(name) {
  if (!name) {
    return
  }
  // RFC 1123 subdomain: dot-separated labels of lower case alphanumerics
  // and '-', each starting and ending with an alphanumeric, 253 chars total.
  var re = /^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$/
  return name.length <= 253 && re.test(name)
}

// Kubernetes namespaces must be DNS labels (RFC 1123), unlike secret names
// which may be DNS subdomains.
function validDnsLabel(name) {
  return /^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$/.test(name)
}

const rules = {
  validNamespace: [
    (value) => !!value || 'Must not be empty',
    (value) => !value || value.length <= 63 || 'Longer than 63 chars',
    (value) =>
      !value ||
      validDnsLabel(value) ||
      "Must consist of lower case alphanumerics or '-', and start and end with an alphanumeric"
  ],
  validDnsSubdomain: [
    (value) => !value || value.length <= 253 || 'Longer than 253 chars',
    (value) => !!value || 'Must not be empty',
    (value) =>
      (!!value && /^[a-z0-9-.]*$/.test(value)) ||
      'Invalid char. Must be one of lower chars, digits, dashes or dots.',
    (value) => (!!value && /^[a-z0-9]/.test(value)) || 'Must start with a lower char or digit',
    (value) => (!!value && /[a-z0-9]$/.test(value)) || 'Must end with a lower char or digit',
    (value) => validDnsSubdomain(value) || 'Not a valid DNS subdomain'
  ],
  // Outside the strict scope the secret name is not sealed into the secret.
  // It may stay empty, but a given name still has to be a valid one.
  optionalDnsSubdomain: [
    (value) => !value || value.length <= 253 || 'Longer than 253 chars',
    (value) =>
      !value ||
      validDnsSubdomain(value) ||
      "Must consist of lower case alphanumerics, '-' or '.', and start and end with an alphanumeric"
  ],
  validSecretKey: [
    (value) => !!value || 'Must not be empty',
    (value) =>
      (!!value && /^[a-z0-9_.-]*$/i.test(value)) ||
      'Invalid char. Must be one of lower chars, digits, dash, underscore or dot.'
  ],
  // A single-file input validates one File, a multi-file input an array.
  fileSize: [(files) => !files || ![files].flat().some(isFileTooLarge) || FILE_TOO_LARGE_MESSAGE]
}

function isFileTooLarge(file) {
  return file.size > MAX_FILE_SIZE_BYTES
}

const incompleteSecretData = computed(() => secrets.value.some((entry) => !isEntryComplete(entry)))

const invalidNewNamespace = computed(
  () =>
    newNamespace.value && scopeNeedsNamespace(scope.value) && !validDnsLabel(namespaceName.value)
)

// Failing to list the cluster's namespaces only affects the dropdown, so it
// must not block sealing for a manually entered namespace.
const blockingError = computed(
  () => hasErrorMessage.value && !(newNamespace.value && errorSource.value === 'namespaces')
)

// A secret name is optional outside the strict scope, but a name that is not
// a valid DNS subdomain would end up as broken YAML in the result.
const invalidSecretName = computed(() => !!secretName.value && !validDnsSubdomain(secretName.value))

const notReadyToEncode = computed(
  () =>
    blockingError.value ||
    incompleteSecretData.value ||
    invalidNewNamespace.value ||
    invalidSecretName.value ||
    (scopeNeedsNamespace(scope.value) && namespaceName.value === '') ||
    (scopeNeedsName(scope.value) && secretName.value === '')
)

const renderedSecrets = computed(() => renderSecrets(sealedSecrets.value))
const sealedSecretsAnnotations = computed(() => {
  if (scope.value === SCOPE_STRICT) {
    return '{}'
  }
  return `{ sealedsecrets.bitnami.com/${scope.value}: "true" }`
})

function findEntry(id) {
  return secrets.value.find((entry) => entry.id === id)
}

function updateEntry(id, changes) {
  Object.assign(findEntry(id), changes)
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

function setErrorMessage(newErrorMessage, source = '') {
  errorMessage.value = newErrorMessage
  errorSource.value = newErrorMessage ? source : ''
  hasErrorMessage.value = !!newErrorMessage
  showErrorSnackbar.value = !!newErrorMessage
}

async function fetchNamespacesData(config) {
  try {
    namespaces.value = await fetchNamespaces(config)
  } catch (error) {
    log.error('Failed to fetch namespaces:', error)
    setErrorMessage(`Failed to fetch namespaces. Error Message: ${error.message}.`, 'namespaces')
  }
}

function toggleFavorite(namespace) {
  if (favoriteNamespaces.value.has(namespace)) {
    favoriteNamespaces.value.delete(namespace)
  } else {
    favoriteNamespaces.value.add(namespace)
  }
  localStorage.favoriteNamespaces = JSON.stringify([...favoriteNamespaces.value])
}

async function fetchDisplayName(config) {
  displayName.value = config.display_name
}

async function fetchEncodedSecrets() {
  try {
    loading.value = true
    sealedSecrets.value = await fetchEncodedSecretsApi(await getConfig(), {
      secretName: secretName.value,
      namespaceName: namespaceName.value,
      scope: scope.value,
      secrets: secrets.value
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

const renderSecrets = (sealedSecrets) => {
  const dataEntries = sealedSecrets.map((element) => `    ${element['key']}: ${element['value']}`)
  return '\n' + dataEntries.join('\n')
}

async function copyRenderedSecrets() {
  // Access the nested ref through the SecretsResults component
  const sealedSecretElement = secretsResultsRef.value?.sealedSecretCardRef?.$refs?.sealedSecretRef
  if (!sealedSecretElement) {
    log.error('Could not access sealed secret element')
    return
  }
  const sealedSecretContent = sealedSecretElement.innerText.trim()
  const copied = await copyToClipboard(sealedSecretContent)
  if (!copied) {
    setErrorMessage('Failed to copy sealed secret to clipboard.')
    return
  }
  clipboardMessage.value = 'Sealed secret copied to clipboard!'
  clipboardSnackbar.value = true
  isCopiedMain.value = true
  setTimeout(() => {
    isCopiedMain.value = false
  }, COPIED_FEEDBACK_MS)
}

async function copySealedSecret(counter) {
  const copied = await copyToClipboard(sealedSecrets.value[counter].value)
  if (!copied) {
    setErrorMessage('Failed to copy secret value to clipboard.')
    return
  }
  clipboardMessage.value = `Secret key "${sealedSecrets.value[counter].key}" copied to clipboard!`
  clipboardSnackbar.value = true
  copiedIndividual.value[counter] = true
  setTimeout(() => {
    copiedIndividual.value[counter] = false
  }, COPIED_FEEDBACK_MS)
}

// The list never becomes empty: removing the only row leaves a blank one.
function removeEntry(id) {
  const remaining = secrets.value.filter((entry) => entry.id !== id)
  secrets.value = remaining.length > 0 ? remaining : [createSecretEntry()]
}

function removeAllEntries() {
  secrets.value = [createSecretEntry()]
}

function resetSealedSecretImport() {
  importMenuOpen.value = false
  availableSealedSecrets.value = []
  selectedSealedSecret.value = null
}

async function loadSealedSecretsForNamespace() {
  if (!namespaceName.value || !sealedSecretImportFeatureEnabled.value) {
    availableSealedSecrets.value = []
    selectedSealedSecret.value = null
    return
  }

  try {
    loadingSealedSecrets.value = true
    availableSealedSecrets.value = await fetchSealedSecrets(await getConfig(), namespaceName.value)
  } catch (error) {
    log.error(
      `Failed to fetch existing SealedSecrets in namespace "${namespaceName.value}":`,
      error
    )
    setErrorMessage(`Failed to fetch existing SealedSecrets. Error Message: ${error.message}.`)
    availableSealedSecrets.value = []
    selectedSealedSecret.value = null
  } finally {
    loadingSealedSecrets.value = false
  }
}

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

watch(namespaceName, () => {
  confirmOverwriteDialog.value = false
  pendingNewSealedSecret.value = null
  availableSealedSecrets.value = []
  selectedSealedSecret.value = null
  importMenuOpen.value = false
})

async function onImportMenuOpen() {
  if (!availableSealedSecrets.value.length) {
    await loadSealedSecretsForNamespace()
  }
}

watch(selectedSealedSecret, (newSealedSecret) => {
  if (!newSealedSecret || !Array.isArray(newSealedSecret.keys)) {
    return
  }
  if (hasUserEnteredSecretData()) {
    pendingNewSealedSecret.value = newSealedSecret
    confirmOverwriteDialog.value = true
    return
  }
  applySelectedSealedSecret(newSealedSecret)
})

function applySelectedSealedSecret(sealedSecret) {
  const entries = sealedSecret.keys.map((key) => createSecretEntry({ key }))
  secrets.value = entries.length > 0 ? entries : [createSecretEntry()]
}

function confirmOverwrite() {
  confirmOverwriteDialog.value = false
  if (pendingNewSealedSecret.value) {
    applySelectedSealedSecret(pendingNewSealedSecret.value)
    pendingNewSealedSecret.value = null
  }
}

function cancelOverwrite() {
  confirmOverwriteDialog.value = false
  pendingNewSealedSecret.value = null
  selectedSealedSecret.value = null
}

async function getConfig() {
  if (!Object.keys(config.value).length) {
    config.value = await fetchConfig()
  }
  return config.value
}

function hasUserEnteredSecretData() {
  return secrets.value.some((entry) => !isEntryBlank(entry))
}
</script>
