<template>
  <div class="secrets-component">
    <div
      v-if="displayCreateSealedSecretForm"
      class="secrets-form"
    >
    <v-container
      v-if="displayName"
      class="text-subtitle-1"
      align="center"
    >
      {{ displayName }}
    </v-container>
    <v-row justify="end">
      <v-col
      cols="3"
      sm="3"
      md="3"
      >
        <v-select
        v-model="selectedEnvironment"
        :items="Object.keys(environments)"
        :select-size="1"
        :plain="true"
        label="Select Environment"
        variant="outlined"
        />
      </v-col>
    </v-row>
    <v-divider class="mt-2 mb-6"></v-divider>
      <v-form>
        <v-row>
          <v-col
            cols="12"
            sm="6"
            md="4"
          >
            <v-autocomplete
              v-model="namespaceName"
              :items="namespaces"
              label="Namespace name"
              :disabled="['strict', 'namespace-wide'].indexOf(scope) === -1"
              variant="solo-inverted"
            />
            <v-container
              id="password-help-block"
              class="text-caption"
            >
              Select the target namespace where the sealed secret will be
              deployed.
            </v-container>
          </v-col>
          <v-col
            cols="12"
            sm="6"
            md="4"
          >
            <v-text-field
              id="input-secret-name"
              v-model="secretName"
              label="Secret name"
              trim
              clearable
              variant="solo-inverted"
              :rules="rules.validDnsSubdomain"
              :disabled="['strict'].indexOf(scope) === -1"
            />
            <v-container
              id="password-help-block"
              class="text-caption"
            >
              Specify name of the secret.
              <br>
              <i>The secret name must be of type:
                <a
                  target="_blank"
                  href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
                >DNS Subdomain</a></i>
            </v-container>
          </v-col>
          <v-col
            cols="12"
            md="4"
          >
            <v-select
              v-model="scope"
              :items="scopes"
              :select-size="1"
              :plain="true"
              label="Scope"
              variant="solo-inverted"
            />
            <v-container
              id="scope-help-block"
              class="text-caption"
            >
              Specify scope of the secret.
              <br>
              <i>
                <a
                  target="_blank"
                  href="https://github.com/bitnami-labs/sealed-secrets#scopes"
                >Scopes for sealed secrets</a></i>
            </v-container>
          </v-col>
        </v-row>

        <v-row
          v-for="(secret, counter) in secrets"
          :key="counter"
        >
          <v-col
            cols="12"
            md="4"
          >
            <v-textarea
              v-model="secret.key"
              label="Secret key"
              rows="1"
              clearable
              prepend-icon="mdi-delete"
              variant="solo-inverted"
              :rules="rules.validSecretKey"
              @click:prepend="removeSecret(counter)"
            />
          </v-col>
          <v-col
            cols="12"
            :sm="hasValue[counter] ? 11 : hasFile[counter] ? 1 : 6"
            :md="hasValue[counter] ? 7 : hasFile[counter] ? 1 : 4"
          >
            <v-textarea
              v-model="secret.value"
              rows="1"
              auto-grow
              clearable
              label="Secret value"
              variant="solo-inverted"
              :disabled="hasFile[counter]"
            />
          </v-col>
          <v-col
            cols="12"
            :sm="hasFile[counter] ? 11 : hasValue[counter] ? 1 : 6"
            :md="hasFile[counter] ? 7 : hasValue[counter] ? 1 : 4"
          >
            <v-file-input
              v-model="secret.file"
              show-size
              dense
              clearable
              label="Upload File"
              prepend-icon="mdi-file-upload-outline"
              variant="outlined"
              :rules="rules.fileSize"
              :disabled="hasValue[counter]"
              :multiple="false"
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-btn
            prepend-icon="mdi-plus-box"
            color="accent"
            @click="secrets.push({ key: '', value: '', file: [] })"
            >
            Add key-value pair
          </v-btn>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-container
          class="text-caption"
          block
          >
          Specify sensitive value and corresponding key of the secret.
          <br>
          <i>The key must be of type:
            <a
            target="_blank"
            href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
            >DNS Subdomain</a></i>
          </v-container>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-alert
          v-model="hasErrorMessage"
          closable
          prominent
          border="start"
          type="warning"
              icon="mdi-flash"
              title="An Error occurred:"
            >
              <v-container>
                <p>Please contact your administrator and try again later.</p>
                <b>Error message:</b>
                <p>
                  <code class="ma-4">{{ errorMessage }}</code>
                </p>
              </v-container>
            </v-alert>
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col
            cols="6"
            sm="3"
          >
            <v-btn
              block
              variant="tonal"
              prepend-icon="mdi-lock"
              color="blue lighten-1"
              :disabled="notReadyToEncode"
              @click="fetchEncodedSecrets()"
            >
              Encrypt
            </v-btn>
            <v-container
              v-if="isEncryptButtonDisabled && !hasErrorMessage"
              class="text-caption mt-2"
              align="center"
            >
              Please fill out the form before encrypting.
            </v-container>
          </v-col>
        </v-row>
      </v-form>
    </div>
    <div v-else>
      <v-row>
        <v-col>
          <v-card
            title="Complete sealed secret"
            class="ma-2"
          >
            <template #text>
              <v-code
                id="sealed-secret-result"
                class="overflow-auto"
              >
                <pre
                  ref="sealedSecret"
                  class="output"
                >
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: {{ secretName ? secretName : "# no secret name given" }}
  namespace: {{ namespaceName ? namespaceName : "# no namespace name given" }}
  annotations: {{ sealedSecretsAnnotations }}
spec:
  encryptedData: {{ renderedSecrets }}</pre>
              </v-code>
            </template>
            <template #actions>
              <v-btn
                v-if="clipboardAvailable"
                variant="text"
                @click="copyRenderedSecrets()"
              >
                Copy to clipboard
              </v-btn>
              <v-spacer />
              <v-btn
                v-if="clipboardAvailable"
                icon="mdi-content-copy"
                @click="copyRenderedSecrets()"
              />
            </template>
          </v-card>
        </v-col>
      </v-row>
      <v-row
        dense
        align-content="center"
      >
        <v-card
          v-for="(secret, counter) in sealedSecrets"
          :key="counter"
          class="s4 ma-2"
          max-width="400"
        >
          <template #title>
            Key <code>{{ secret["key"] }}</code>
          </template>
          <template #text>
            <v-code class="overflow-auto">
              <pre class="output">{{ secret["value"] }}</pre>
            </v-code>
          </template>
          <template #actions>
            <v-btn
              v-if="clipboardAvailable"
              variant="text"
              @click="copySealedSecret(counter)"
            >
              Copy to clipboard
            </v-btn>
            <v-spacer />
            <v-btn
              v-if="clipboardAvailable"
              icon="mdi-content-copy"
              variant="text"
              @click="copySealedSecret(counter)"
            />
          </template>
        </v-card>
      </v-row>
      <v-row justify="center">
        <v-col 
        class="d-flex"
        cols="7"
        sm="4">
          <v-btn
            block
            variant="tonal"
            class="flex-fill"
            prepend-icon="mdi-autorenew"
            @click="resetForm"
          >
            Encrypt more secrets
          </v-btn>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeMount, onMounted, watch } from 'vue'
import { Base64 } from "js-base64";

let config;

onBeforeMount(async () => {
  config = await fetchConfig();
  await fetchNamespaces();
  await fetchDisplayName(config);
  await fetchEnvironments(config);

  // Assuming you have a default environment or set the selectedEnvironment accordingly
  selectedEnvironment.value = Object.keys(environments?.value)[0];
})

const namespaces = ref([])
const scopes = ref(["strict", "cluster-wide", "namespace-wide"])
const errorMessage = ref("")
const hasErrorMessage = ref(false)
const displayName = ref("")
const displayCreateSealedSecretForm = ref(true)
const secretName = ref("")
const namespaceName = ref("")
const scope = ref("strict")
const secrets = ref([{ key: "", value: "", file: [] }])
const sealedSecrets = ref([])
const sealedSecret = ref()
const clipboardAvailable = ref(false)
const selectedEnvironment = ref("")
const environments = ref({})

const resetErrorState = () => {
  setErrorMessage("");
  hasErrorMessage.value = false;
};

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

watch(selectedEnvironment, async (newSelectedEnvironment) => {
  if (newSelectedEnvironment) {
    resetErrorState();
    await fetchNamespaces();
  }
});


onMounted(() => {
  if (navigator && navigator.clipboard) {
    clipboardAvailable.value = true;
  }
  setErrorMessage("");
})

function validDnsSubdomain(name) {
  if (!name) {
    return;
  }
  var re = /^[a-z0-9]([a-z0-9._-]{0,251}[a-z0-9])?$/;
  return re.test(name);
}

function readFileAsync(file) {
  return new Promise((resolve, reject) => {
    let reader = new FileReader();
    reader.onload = () => {
      resolve(reader.result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
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
  scope.value === "strict" && (namespaceName.value === "" || secretName.value === "") ||
  scope.value === "namespace-wide" && namespaceName.value === ""
)

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

const selectedApiUrl = computed(() => environments?.value[selectedEnvironment.value] || config?.api_url);


function setErrorMessage(newErrorMessage) {
  errorMessage.value = newErrorMessage;
  hasErrorMessage.value = !!newErrorMessage;
}

const isEncryptButtonEnabled = computed(() => {
  return (
    secretName.value &&
    namespaceName.value &&
    secrets.value.every(secret => secret.key && (secret.value || secret.file.length))
  );
});
async function fetchConfig() {
  try {
    const response = await fetch("/config.json");
    if (!response.ok) {
      throw Error(`Failed to fetch config.json: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    setErrorMessage(error.message);
    return {};
  }
}

async function fetchNamespaces() {
  try {
    
    const response = await fetch(`${selectedApiUrl.value}/namespaces`);
    
    namespaces.value = await response.json();
  } catch (error) {
    namespaces.value = [];
    setErrorMessage(`Failed to fetch namespaces. Error Message: ${error.message}.`);
  }
}

async function fetchDisplayName(config) {
  displayName.value = config.display_name;
}

async function fetchEnvironments(config) {
  try {
    if (!config.environments || Object.keys(config.environments).length === 0) {
      // If environments are not defined or empty, use the default API URL
      environments.value = { default: config.api_url };
    } else {
      // If environments are defined in config.json, use them
      environments.value = config.environments;
    }
  } catch (error) {
    setErrorMessage(error);
  }
}

async function fetchEncodedSecrets() {
  try {
    const requestObject = {
      secret: secretName.value,
      namespace: namespaceName.value,
      scope: scope.value,
      secrets: await Promise.all(
        secrets.value.map(async (element) => {
          if (element.value) {
            return {
              key: element.key,
              value: Base64.encode(element.value),
            };
          } else {
            let fileContent = await readFileAsync(element.file);
            // we get a dataurl, so split the header from the data and use data, only
            fileContent = fileContent.split(",")[1];
            return {
              key: element.key,
              file: fileContent,
            };
          }
        })
      ),
    };

    const requestBody = JSON.stringify(requestObject, null, "\t");

    const response = await fetch(`${selectedApiUrl.value}/secrets`, {
      method: "POST",
      headers: {
        // 'Origin': 'http://localhost:8080',
        "Content-Type": "application/json",
      },
      body: requestBody,
    });

    if (!response.ok) {
      throw Error(
        "No sealed secrets in response from backend: " +
        (await response.text())
      );
    } else {
      sealedSecrets.value = await response.json();
      displayCreateSealedSecretForm.value = false;
      setErrorMessage("");
    }
  } catch (error) {
    setErrorMessage(error);
  }
}

const renderSecrets = (sealedSecrets) => {
  const dataEntries = sealedSecrets.map((element) =>
    `    ${element["key"]}: ${element["value"]}`
  );
  return "\n" + dataEntries.join("\n");
}

function copyRenderedSecrets() {
  const sealedSecretContent = sealedSecret.value.innerText.trim();
  navigator.clipboard.writeText(sealedSecretContent);
}

function copySealedSecret(counter) {
  navigator.clipboard.writeText(sealedSecrets.value[counter].value);
}

function removeSecret(counter) {
  if (secrets.value.length > 1) {
    secrets.value.splice(counter, 1);
  } else {
    secrets.value[0] = { key: "", value: "", file: [] }
  }
}
</script>

<style>
.helper-info {
  margin-bottom: 10px;
}
</style>
