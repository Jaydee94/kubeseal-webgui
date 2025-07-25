<template>
  <div class="secrets-component">
    <v-container
      v-if="displayName"
      class="text-subtitle-1"
      align="center"
    >
      {{ displayName }}
    </v-container>
    <div
      v-if="displayCreateSealedSecretForm"
      class="secrets-form"
    >
      <br>
      <v-form>
        <v-row>
          <v-col
            cols="12"
            sm="6"
            md="4"
          >
          <v-autocomplete
            id="namespaceSelection"
            v-model="namespaceName"
            :items="sortedNamespaces"
            ref="namespaceSelector"
            label="Namespace name"
            variant="solo-inverted"
            :disabled="['strict', 'namespace-wide'].indexOf(scope) === -1"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item
                v-bind="props"
                :value="item"
               >
                <template v-slot:prepend>
                  <v-icon
                  small
                  color="#FFA500"
                  @click.stop="toggleFavorite(item.value)"
                  >
                    {{ favoriteNamespaces.has(item.value) ? 'mdi-heart' : 'mdi-heart-outline' }}
                  </v-icon>
                </template>
              </v-list-item>
              <v-divider v-if="item.value === lastFavoriteNamespace" :thickness="2"></v-divider>
            </template>
          </v-autocomplete>
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
              id="secretName"
              v-model="secretName"
              label="Secret name"
              trim
              clearable
              variant="solo-inverted"
              :rules="rules.validDnsSubdomain"
              :error-messages="secretNameError"
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
              id="secretKey"
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
              id="secretValue"
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
              id="fileInput"
              v-model="secret.file"
              show-size
              dense
              clearable
              label="Upload File"
              prepend-icon="mdi-file-upload-outline"
              variant="solo-inverted"
              :rules="rules.fileSize"
              :error-messages="fileErrors[counter]"
              :disabled="hasValue[counter]"
              :multiple="false"
              @change="validateFile(secret.file, counter)"
            />
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
            <v-btn
              prepend-icon="mdi-delete"
              color="grey lighten-2"
              class="text-caption"
              style="text-transform: none;"
              @click="removeAllSecrets"
            >
              Remove all KEY-VALUE pairs
            </v-btn>
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col
            cols="12"
            sm="6"
          >
            <v-btn
              block
              variant="plain"
              size="x-large"
              prepend-icon="mdi-lock"
              color="blue lighten-1"
              :disabled="notReadyToEncode"
              @click="fetchEncodedSecrets()"
            >
              Encrypt
            </v-btn>
            <v-card
              v-if="!isEncryptButtonEnabled && !hasErrorMessage"
              variant="text"
              class="text-subtitle-2 mt-5"
              color="light-blue-accent-4"
              align="center"
            >
              Fill out the form before encrypting.
            </v-card>
          </v-col>
        </v-row>
      </v-form>
    </div>
    <div v-else>
      <v-row>
        <v-col>
          <v-card
            title="Generated sealed secret"
            class="ma-1"
          >
            <template #text>
              <pre class="overflow-auto"><v-code
                id="sealed-secret-result"
                class="overflow-auto"
                ref="sealedSecret"
              >apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: {{ secretName ? secretName : "# no secret name given" }}
  namespace: {{ namespaceName ? namespaceName : "# no namespace name given" }}
  annotations: {{ sealedSecretsAnnotations }}
spec:
  encryptedData: {{ renderedSecrets }}</v-code></pre>
            </template>
            <template #actions>
              <v-btn
                v-if="clipboardAvailable"
                variant="text"
                prepend-icon="mdi-content-copy"
                @click="copyRenderedSecrets()"
              >
                Copy to clipboard
              </v-btn>
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
            <pre class="overflow-auto"><v-code class="overflow-auto">{{ secret["value"] }}</v-code></pre>
          </template>
          <template #actions>
            <v-btn
              v-if="clipboardAvailable"
              variant="text"
              prepend-icon="mdi-content-copy"
              @click="copySealedSecret(counter)"
            >
              Copy to clipboard
            </v-btn>
          </template>
        </v-card>
      </v-row>
      <v-row>
        <v-col class="d-flex">
          <v-btn
            block
            variant="plain"
            class="flex-fill"
            prepend-icon="mdi-delete"
            @click="resetForm"
          >
            Clear secrets
          </v-btn>
        </v-col>
        <v-col class="d-flex">
          <v-btn
            block
            variant="plain"
            class="flex-fill"
            prepend-icon="mdi-pencil"
            @click="displayCreateSealedSecretForm=true"
          >
            Edit secrets
          </v-btn>
        </v-col>
      </v-row>
    </div>
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
import { ref, computed, onBeforeMount, onMounted, useTemplateRef } from 'vue'
import { Base64 } from "js-base64";

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
const favoriteNamespaces = ref(readFavoriteNamespaces());
const showErrorSnackbar = ref(false);
const clipboardSnackbar = ref(false);
const clipboardMessage = ref("");
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
  await fetchNamespaces(config);
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
  } catch (error) {
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

const adjectives = [
    "altered", "angry", "big", "blinking", "boring", "broken", "bubbling", "calculating",
    "cute", "diffing", "expensive", "fresh", "fierce", "floating", "generous", "golden",
    "green", "growing", "hidden", "hideous", "interesting", "kubed", "mumbling", "rusty",
    "singing", "small", "sniffing", "squared", "talking", "trusty", "wise", "walking", "zooming"
];

const nouns = [
    "ant", "bike", "bird", "captain", "cheese", "clock", "digit", "gorilla", "kraken", "number",
    "maven", "monitor", "moose", "moon", "mouse", "news", "newt", "octopus", "opossum", "otter",
    "paper", "passenger", "potato", "ship", "spaceship", "spaghetti", "spoon", "store", "tomcat",
    "trombone", "unicorn", "vine", "whale"
];

function mockNamespacesResolver(count) {
    const randomPairs = new Set();
    while (randomPairs.size < count) {
        const adjective = adjectives[Math.floor(Math.random() * adjectives.length)];
        const noun = nouns[Math.floor(Math.random() * nouns.length)];
        randomPairs.add(`${adjective}-${noun}`);
    }
    return Array.from(randomPairs).sort();
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

async function fetchNamespaces(config) {
  if (import.meta.env.VITE_MOCK_NAMESPACES) {
    namespaces.value = mockNamespacesResolver(10);
  } else {
    try {
      const response = await fetch(`${config.api_url}/namespaces`);
      namespaces.value = await response.json();
    } catch (error) {
      setErrorMessage(`Failed to fetch namespaces. Error Message: ${error.message}.`);
    }
  }
}

const sortedNamespaces = computed(() => {
  return [
    ...liveFavoriteNamespaces.value,
    ...namespaces.value.filter((namespace) => !favoriteNamespaces.value.has(namespace))
  ];
});

const liveFavoriteNamespaces = computed(
  () => Array.from(favoriteNamespaces.value).filter(
    (namespace) => namespaces.value.includes(namespace)
  )
)

const lastFavoriteNamespace = computed(
  () => liveFavoriteNamespaces.value.length > 0 ? liveFavoriteNamespaces.value[liveFavoriteNamespaces.value.length - 1] : ""
)

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

    const config = await fetchConfig()

    const response = await fetch(`${config.api_url}/secrets`, {
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
  const sealedSecretContent = sealedSecret.value.$el.innerText.trim();
  navigator.clipboard.writeText(sealedSecretContent).then(() => {
    clipboardMessage.value = "Sealed secret copied to clipboard!";
    clipboardSnackbar.value = true;
  });
}

function copySealedSecret(counter) {
  navigator.clipboard.writeText(sealedSecrets.value[counter].value).then(() => {
    clipboardMessage.value = `Secret key "${sealedSecrets.value[counter].key}" copied to clipboard!`;
    clipboardSnackbar.value = true;
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
  background-color: rgb(var(--v-theme-code));
  color: rgb(var(--v-theme-on-code));
  padding: 0.2em 0.4em;
}

pre > code.v-code {
  padding: 0 !important;
}
</style>
