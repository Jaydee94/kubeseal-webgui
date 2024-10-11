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
              v-model="namespaceName"
              :items="namespaces"
              label="Namespace name"
              :disabled="['strict', 'namespace-wide'].indexOf(scope) === -1"
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

        <v-row v-for="(secret, counter) in secrets" :key="counter">
          <v-col cols="12" md="4">
            <v-textarea
              v-model="secret.key"
              label="Secret Key"
              rows="1"
              clearable
              prepend-icon="mdi-delete"
              :rules="rules.validSecretKey"
              @click:prepend="removeSecret(counter)"
            />
          </v-col>
          <v-col cols="12" :sm="hasValue[counter] ? 11 : hasFile[counter] ? 1 : 6" :md="hasValue[counter] ? 7 : hasFile[counter] ? 1 : 4">
            <v-textarea
              v-model="secret.value"
              rows="1"
              auto-grow
              clearable
              label="Secret Value"
              :disabled="hasFile[counter]"
            >
              <template v-slot:prepend>
                <v-tooltip bottom>
                  <template v-slot:activator="{ props }">
                    <v-icon
                      v-bind="props"
                      @click="secrets[counter].menuVisible = !secrets[counter].menuVisible"
                      v-if="enableRandomStringGenerator"
                    >
                      mdi-dice-multiple
                    </v-icon>
                  </template>
                  <span>Generate Random String</span>
                </v-tooltip>
              </template>
            </v-textarea>
            <v-menu
              v-model="secrets[counter].menuVisible" 
              :close-on-content-click="false"
              absolute
              offset-y
              v-if="enableRandomStringGenerator"
            >
              <template v-slot:activator="{ props }">
                <v-btn icon v-bind="props" style="display: none;"></v-btn>
              </template>
              <v-list>
                <v-list-item @click.stop>
                  <v-checkbox v-model="includeUppercase" label="Include Uppercase Letters (A-Z)" />
                </v-list-item>
                <v-list-item @click.stop>
                  <v-checkbox v-model="includeLowercase" label="Include Lowercase Letters (a-z)" />
                </v-list-item>
                <v-list-item @click.stop>
                  <v-checkbox v-model="includeNumbers" label="Include Numbers (0-9)" />
                </v-list-item>
                <v-list-item @click.stop>
                  <v-checkbox v-model="includeSpecial" :label="specialCharactersLabel" />
                </v-list-item>
                <v-list-item @click.stop>
                  <v-slider
                    v-model="passwordLength"
                    :min="6"
                    :max="64"
                    step="1"
                    label="Password Length"
                    thumb-label="always"
                    dense
                  >
                    <template v-slot:append>
                      <span>{{ passwordLength }}</span>
                    </template>
                  </v-slider>
                </v-list-item>
                <v-list-item>
                  <v-btn color="primary" @click="generateRandomString(counter); secrets[counter].menuVisible = false;">
                    Generate Random String
                  </v-btn>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-col>
          <v-col cols="12" :sm="hasFile[counter] ? 11 : hasValue[counter] ? 1 : 6" :md="hasFile[counter] ? 7 : hasValue[counter] ? 1 : 4">
            <v-file-input
              v-model="secret.file"
              show-size
              dense
              clearable
              label="Upload File"
              prepend-icon="mdi-file-upload-outline"
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
              title="Error while encoding sensitive data"
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
            cols="12"
            sm="6"
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
      <v-row>
        <v-col class="d-flex">
          <v-btn
            block
            variant="tonal"
            class="flex-fill"
            @click="
              displayCreateSealedSecretForm = !displayCreateSealedSecretForm
              "
          >
            Encrypt more secrets
          </v-btn>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeMount, onMounted } from 'vue'
import { Base64 } from "js-base64";

const namespaces = ref([])
const apiUrl = ref("")
const scopes = ref(["strict", "cluster-wide", "namespace-wide"])
const errorMessage = ref("")
const hasErrorMessage = ref(false)
const displayName = ref("")
const displayCreateSealedSecretForm = ref(true)
const secretName = ref("")
const namespaceName = ref("")
const scope = ref("strict")
const secrets = ref([{ key: "", value: "", file: [], menuVisible: false }]);
const sealedSecrets = ref([])
const sealedSecret = ref()
const clipboardAvailable = ref(false)

const includeUppercase = ref(true);
const includeLowercase = ref(true);
const includeNumbers = ref(true);
const includeSpecial = ref(false);
const passwordLength = ref(10);
const enableRandomStringGenerator = ref(false);
const specialCharacters = ref('');

const specialCharactersLabel = computed(() => {
      return `Include Special Characters (${specialCharacters.value || 'None'})`;
});

onBeforeMount(async () => {
  await fetchConfig();
  document.removeEventListener('click', closeMenu);
})

onMounted(() => {
  if (navigator && navigator.clipboard) {
    clipboardAvailable.value = true;
  }
  document.addEventListener('click', closeMenu);
  setErrorMessage("");
})

function closeMenu() {
  secrets.value.forEach(secret => {
    secret.menuVisible = false;
  });
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

function setErrorMessage(newErrorMessage) {
  errorMessage.value = newErrorMessage;
  hasErrorMessage.value = !!newErrorMessage;
}

async function fetchConfig() {
  try {
    const response = await fetch("/config.json");
    const config = await response.json();
    try {
      const namespacesResponse = await fetch(`${apiUrl.value}/namespaces`);
      namespaces.value = await namespacesResponse.json();
    } catch (error) {
      setErrorMessage(error);
    }
    displayName.value = config.display_name;
    enableRandomStringGenerator.value = config.enable_random_string_generator;
    specialCharacters.value = config.random_string_generator_special_characters;
    apiUrl.value = config.api_url;
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

    const response = await fetch(`${apiUrl.value}/secrets`, {
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

function generateSecureRandomString(length, includeUppercase, includeLowercase, includeNumbers, includeSpecial) {
  const classes = {
    upperCase: { chars: "ABCDEFGHIJKLMNOPQRSTUVWXYZ", enabled: includeUppercase },
    lowerCase: { chars: "abcdefghijklmnopqrstuvwxyz", enabled: includeLowercase },
    digits: { chars: "0123456789", enabled: includeNumbers },
    special: { chars: specialCharacters.value, enabled: includeSpecial }
  };

  const chars = Object.values(classes)
    .filter(v => v.enabled)
    .map(v => v.chars)
    .join('');

  if (chars.length === 0) {
    setErrorMessage('At least one character type must be selected to create a random string.');
    return '';
  }

  let initialResult = '';

  Object.values(classes).forEach(v => {
    if (v.enabled) {
      initialResult += getRandomCharacter(v.chars);
    }
  });
  for (let i = initialResult.length; i < length; i++) {
    initialResult += getRandomCharacter(chars);
  }
  const result = shuffleString(initialResult);
  return result;
}

function shuffleString(str) {
  const array = str.split('');
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
  return array.join('');
}

function getRandomCharacter(charSet) {
    if (charSet.length === 0) {
        throw new Error("Character set cannot be empty");
    }
    const randomValues = new Uint32Array(1);
    window.crypto.getRandomValues(randomValues);
    // Generate a random index within the bounds of charSet length
    // By dividing the random number by 0xFFFFFFFF + 1, you normalize it to a value between 0 and 1.
    // Multiplying this normalized value by charSet.length gives you a floating-point number that scales to the desired range.
    const randomIndex = Math.floor(randomValues[0] / (0xFFFFFFFF + 1) * charSet.length);
  
    return charSet[randomIndex];
}



function generateRandomString(index) {
  const length = passwordLength.value;
  const config = {
    includeUppercase: includeUppercase.value,
    includeLowercase: includeLowercase.value,
    includeNumbers: includeNumbers.value,
    includeSpecial: includeSpecial.value,
  };
  secrets.value[index].value = generateSecureRandomString(length, config.includeUppercase, config.includeLowercase, config.includeNumbers, config.includeSpecial);
}

</script>

<style>
.helper-info {
  margin-bottom: 10px;
}
</style>
