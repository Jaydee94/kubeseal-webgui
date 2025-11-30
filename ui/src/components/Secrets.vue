<template>
  <div class="secrets-component">
    <v-container
      v-if="displayName"
      class="text-h5 text-gradient-primary text-center mb-2 py-0"
      align="center"
    >
      {{ displayName }}
    </v-container>

    <!-- Form and Results Section -->
    <transition name="fade" mode="out-in">
      <div
        v-if="loading"
        class="d-flex justify-center align-center"
        style="min-height: 400px;"
      >
        <v-progress-circular
          indeterminate
          color="primary"
          size="64"
        ></v-progress-circular>
      </div>
      <v-card
        v-else-if="displayCreateSealedSecretForm"
        class="secrets-form modern-card pa-6 mb-6"
        elevation="1"
        variant="outlined"
      >
        <v-form>
          <SecretFormInputs
            v-model:namespace-name="namespaceName"
            v-model:secret-name="secretName"
            v-model:scope="scope"
            :namespaces="namespaces"
            :scopes="scopes"
            :rules="rules"
            :secret-name-error="secretNameError"
            :favorite-namespaces="favoriteNamespaces"
            @toggle-favorite="toggleFavorite"
          />

          <SecretsList
            :secrets="secrets"
            :has-value="hasValue"
            :has-file="hasFile"
            :rules="rules"
            :file-errors="fileErrors"
            @update:secrets="updateSecret"
            @add-secret="secrets.push({ key: '', value: '', file: [] })"
            @remove-secret="removeSecret"
            @remove-all="removeAllSecrets"
            @file-change="validateFile"
          />

          <v-row justify="center">
            <v-col
              cols="12"
              sm="8"
              md="6"
              class="d-flex flex-column align-center"
            >
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
                  v-if="!isEncryptButtonEnabled && !hasErrorMessage"
                  class="text-caption text-medium-emphasis text-center mt-3 d-flex align-center justify-center"
                >
                  <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
                  Please complete all fields to encrypt
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
        @edit="displayCreateSealedSecretForm=true"
      />
    </transition>

    <!-- Snackbars -->
    <v-snackbar
      v-model="showErrorSnackbar"
      color="red"
      timeout="5000"
      top
    >
      <v-icon left>mdi-alert-circle</v-icon>
      {{ errorMessage }}
    </v-snackbar>
    <v-snackbar
      v-model="clipboardSnackbar"
      color="green"
      timeout="3000"
      top
    >
      <v-icon left>mdi-check-circle</v-icon>
      {{ clipboardMessage }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeMount, onMounted } from 'vue'
import SecretFormInputs from './SecretFormInputs.vue'
import SecretsList from './SecretsList.vue'
import SecretsResults from './SecretsResults.vue'
import { useConfig } from '@/composables/useConfig'
import { useSecrets } from '@/composables/useSecrets'

defineOptions({
  name: 'SecretsManager'
})

const { fetchConfig } = useConfig()
const { fetchNamespaces, fetchEncodedSecrets: fetchEncodedSecretsApi } = useSecrets()


const namespaces = ref([])
const scopes = ref(["strict", "cluster-wide", "namespace-wide"])
const errorMessage = ref("")
const hasErrorMessage = ref(false)
const displayName = ref("")
const displayCreateSealedSecretForm = ref(true)
const loading = ref(false)
const secretName = ref("")
const namespaceName = ref("")
const scope = ref("strict")
const secrets = ref([{ key: "", value: "", file: [] }])
const sealedSecrets = ref([])
const secretsResultsRef = ref()
const clipboardAvailable = ref(false)
const favoriteNamespaces = ref(readFavoriteNamespaces());
const showErrorSnackbar = ref(false);
const clipboardSnackbar = ref(false);
const clipboardMessage = ref("");
const isCopiedMain = ref(false);
const copiedIndividual = ref({});
const fileErrors = ref([]);
const secretNameError = computed(() => {
  if (!secretName.value) return "Secret name is required.";
  return "";
});

const resetForm = () => {
  displayCreateSealedSecretForm.value = true;
  secretName.value = "";
  namespaceName.value = "";
  scope.value = "strict";
  secrets.value = [{ key: "", value: "", file: [] }];
  sealedSecrets.value = [];
  hasErrorMessage.value = false;
  errorMessage.value = "";
};

onBeforeMount(async () => {
  const config = await fetchConfig();
  await fetchNamespacesData(config);
  await fetchDisplayName(config);
})

onMounted(() => {
  if (navigator && navigator.clipboard) {
    clipboardAvailable.value = true;
  }
  setErrorMessage("");
})

function readFavoriteNamespaces() {
  try {
    return new Set(JSON.parse(localStorage.favoriteNamespaces));
  } catch {
    return new Set([]);
  }
}

function validDnsSubdomain(name) {
  if (!name) {
    return;
  }
  var re = /^[a-z0-9]([a-z0-9._-]{0,251}[a-z0-9])?$/;
  return re.test(name);
}


const rules = {
  validDnsSubdomain: [
    (value) => value.length < 253 || "Longer than 253 chars",
    (value) => !!value || "Must not be empty",
    (value) =>
      (!!value && /^[a-z0-9-.]*$/.test(value)) ||
      "Invalid char. Must be one of lower chars, digits, dashes or dots.",
    (value) =>
      (!!value && /^[a-z0-9]/.test(value)) ||
      "Must start with a lower char or digit",
    (value) =>
      (!!value && /[a-z0-9]$/.test(value)) ||
      "Must end with a lower char or digit",
    (value) => validDnsSubdomain(value) || "Not a valid DNS subdomain",
  ],
  validSecretKey: [
    (value) => !!value || "Must not be empty",
    (value) =>
      (!!value && /^[a-z0-9_.-]*$/i.test(value)) ||
      "Invalid char. Must be one of lower chars, digits, dash, underscore or dot.",
  ],
  fileSize: [
    (files) =>
      !files ||
      !files.some((file) => file.size > 1048576) ||
      "File size should be less than 1 MB!",
  ]
}

const incompleteSecretData = computed(() =>
  secrets.value
    .some((e) =>
      e.key === "" ||
      (
        e.value === "" &&
        !(e.file instanceof Blob || e.file instanceof File)
      )
  )
)

const notReadyToEncode = computed(() =>
  hasErrorMessage.value ||
  incompleteSecretData.value ||
  (scope.value === "strict" && (namespaceName.value === "" || secretName.value === "")) ||
  (scope.value === "namespace-wide" && namespaceName.value === "")
);

const hasFile = computed(() =>
  secrets.value.map((e) => e.file instanceof Blob || e.file instanceof File))
const hasValue = computed(() =>
  secrets.value.map((e) => e.value !== "")
)
const renderedSecrets = computed(() =>
  renderSecrets(sealedSecrets.value)
)
const sealedSecretsAnnotations = computed(() => {
  if (scope.value === "strict") {
    return '{}';
  }
  return `{ sealedsecrets.bitnami.com/${scope.value}: "true" }`;
})



// Helper method to update individual secret fields from child components
function updateSecret({ index, field, value }) {
  secrets.value[index][field] = value;
}

function setErrorMessage(newErrorMessage) {
  errorMessage.value = newErrorMessage;
  hasErrorMessage.value = !!newErrorMessage;
  showErrorSnackbar.value = !!newErrorMessage;
}

const isEncryptButtonEnabled = computed(() => {
  return (
    secretName.value &&
    namespaceName.value &&
    secrets.value.every(secret => secret.key && (
      secret.value || secret.file instanceof Blob || secret.file instanceof File
    ))
  );
});

async function fetchNamespacesData(config) {
  try {
    namespaces.value = await fetchNamespaces(config);
  } catch (error) {
    setErrorMessage(`Failed to fetch namespaces. Error Message: ${error.message}.`);
  }
}



function toggleFavorite(namespace) {
  if (favoriteNamespaces.value.has(namespace)) {
    favoriteNamespaces.value.delete(namespace);
  } else {
    favoriteNamespaces.value.add(namespace);
  }
  localStorage.favoriteNamespaces = JSON.stringify([...favoriteNamespaces.value]);
}

async function fetchDisplayName(config) {
  displayName.value = config.display_name;
}

async function fetchEncodedSecrets() {
  try {
    loading.value = true;
    const config = await fetchConfig();
    sealedSecrets.value = await fetchEncodedSecretsApi(config, {
      secretName: secretName.value,
      namespaceName: namespaceName.value,
      scope: scope.value,
      secrets: secrets.value
    });
    // Add a small delay to make the transition noticeable and smooth
    await new Promise(resolve => setTimeout(resolve, 600));
    displayCreateSealedSecretForm.value = false;
    setErrorMessage("");
  } catch (error) {
    setErrorMessage(error.message || error);
  } finally {
    loading.value = false;
  }
}

const renderSecrets = (sealedSecrets) => {
  const dataEntries = sealedSecrets.map((element) =>
    `    ${element["key"]}: ${element["value"]}`
  );
  return "\n" + dataEntries.join("\n");
}

function copyRenderedSecrets() {
  // Access the nested ref through the SecretsResults component
  const sealedSecretElement = secretsResultsRef.value?.sealedSecretCardRef?.$refs?.sealedSecretRef;
  if (!sealedSecretElement) {
    console.error('Could not access sealed secret element');
    return;
  }
  const sealedSecretContent = sealedSecretElement.innerText.trim();
  navigator.clipboard.writeText(sealedSecretContent).then(() => {
    clipboardMessage.value = "Sealed secret copied to clipboard!";
    clipboardSnackbar.value = true;
    isCopiedMain.value = true;
    setTimeout(() => {
      isCopiedMain.value = false;
    }, 2000);
  });
}

function copySealedSecret(counter) {
  navigator.clipboard.writeText(sealedSecrets.value[counter].value).then(() => {
    clipboardMessage.value = `Secret key "${sealedSecrets.value[counter].key}" copied to clipboard!`;
    clipboardSnackbar.value = true;
    copiedIndividual.value[counter] = true;
    setTimeout(() => {
      copiedIndividual.value[counter] = false;
    }, 2000);
  });
}

function removeSecret(counter) {
  if (secrets.value.length > 1) {
    secrets.value.splice(counter, 1);
  } else {
    secrets.value[0] = { key: "", value: "", file: [] }
  }
}

function removeAllSecrets() {
  secrets.value = [{ key: "", value: "", file: [] }];
}

function validateFile(file, counter) {
  const fileSizeRule = rules.fileSize[0];
  const isValid = fileSizeRule([file]) === true;

  if (!isValid) {
    setErrorMessage("File size should be less than 1 MB!");
    secrets.value[counter].file = []; // Clear the invalid file
    fileErrors.value[counter] = "File size should be less than 1 MB!";
  } else {
    setErrorMessage("");
    fileErrors.value[counter] = "";
  }

  // Ensure the `secrets` array is updated to reflect the cleared state
  secrets.value = [...secrets.value];
}
</script>

<style>
.helper-info {
  margin-bottom: 10px;
}

pre:has(code) {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  color: rgb(var(--v-theme-on-surface));
  padding: 12px;
  border-radius: var(--radius-md, 12px);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

pre > code {
  padding: 0 !important;
  background: transparent !important;
  color: inherit !important;
}

.secrets-component {
  max-width: 1600px;
  margin: 0 auto;
  min-height: 400px;
}

.copy-btn {
  transition: all var(--transition-fast, 0.15s ease) !important;
}

.copy-btn:hover {
  transform: scale(1.1);
}

.secrets-form {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modern-input {
  transition: all var(--transition-fast, 0.15s ease);
}

.encrypt-btn {
  font-size: 1rem !important;
  font-weight: 500 !important;
  transition: all var(--transition-fast, 0.15s ease) !important;
}

.result-code {
  border-radius: var(--radius-md, 12px);
  padding: 1rem;
  font-size: 0.875rem;
  line-height: 1.6;
}

.key-code {
  background: linear-gradient(135deg, rgba(0, 123, 255, 0.1), rgba(253, 126, 20, 0.1));
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm, 8px);
  font-weight: 600;
}

/* Transition Classes */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base, 0.3s ease);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active {
  transition: all var(--transition-base, 0.3s ease);
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(30px);
}
</style>
