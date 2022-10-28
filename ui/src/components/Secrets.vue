<template>
  <div class="secrets-component">
    <h3
      v-if="displayName"
      align="center"
    >
      {{ displayName }}
    </h3>
    <div
      v-if="displayCreateSealedSecretForm"
      class="secrets-form"
    >
      <div
        class="helper-info"
        align="right"
      >
        <v-btn
          id="help"
          variant="text"
          icon="mdi-help"
          class="ma-2"
        >
          <v-icon>mdi-help</v-icon>
          <v-tooltip activator="parent">
            <div>
              Usage
            </div>
            <div align="left">
              The entered values will be encrypted using the <b>kubeseal</b> cli.
            </div>
            <div align="left">
              Kubeseal encrypts a plaintext secret using a configured public key.
            </div>
            <br>
            <div align="left">
              You can encrypt multiple <b>&lt;key&gt; &lt;value&gt;</b> pairs
              inside one
            </div>
            <div align="left">
              Kubernetes secret object.
            </div>
            <br>
            <div align="left">
              For more information about <b>sealed-secrets</b>
              <a
                target="_blank"
                href="https://github.com/bitnami-labs/sealed-secrets"
              >click here</a>.
            </div>
          </v-tooltip>
        </v-btn>
      </div>

      <v-form>
        <v-row class="d-flex">
          <v-col>
            <v-autocomplete
              v-model="namespaceName"
              :items="namespaces"
              label="Namespace name"
              :disabled="['strict', 'namespace-wide'].indexOf(scope) === -1"
            />
            <v-container id="password-help-block">
              Select the target namespace where the sealed secret will be
              deployed.
            </v-container>
          </v-col>
          <v-col>
            <v-text-field
              id="input-secret-name"
              v-model="secretName"
              label="Secret name"
              trim
              :rules="rules.validDnsSubdomain"
              :disabled="['strict'].indexOf(scope) === -1"
            />
            <v-container id="password-help-block">
              Specify name of the secret.
              <br>
              <i>The secret name must be of type:
                <a
                  target="_blank"
                  href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
                >DNS
                  Subdomain</a></i>
            </v-container>
          </v-col>
          <v-col>
            <v-select
              v-model="scope"
              :items="scopes"
              :select-size="1"
              :plain="true"
              label="Scope"
            />
            <v-container id="scope-help-block">
              Specify scope of the secret.
              <br>
              <i>
                <a
                  target="_blank"
                  href="https://github.com/bitnami-labs/sealed-secrets#scopes"
                >Scopes for sealed
                  secrets</a></i>
            </v-container>
          </v-col>
        </v-row>

        <v-row
          v-for="(secret, counter) in secrets"
          :key="counter"
        >
          <v-col cols="3">
            <v-textarea
              v-model="secret.key"
              label="Secret key"
              rows="1"
              clearable
              :rules="rules.validDnsSubdomain"
            />
          </v-col>
          <v-col>
            <v-textarea
              v-model="secret.value"
              rows="1"
              auto-grow
              clearable
              label="Secret value"
              :disabled="hasFile[counter]"
            />
          </v-col>
          <v-col cols="2">
            <v-file-input
              v-model="secret.file"
              show-size
              dense
              label="Upload File"
              prepend-icon="mdi-file-upload-outline"
              :rules="fileSize"
              :disabled="hasValue[counter]"
            />
          </v-col>
          <v-col cols="1">
            <v-btn
              icon="mdi-delete"
              variant="text"
              :disabled="hasNoSecrets"
              @click="removeSecret(counter)"
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
            <v-container block>
              Specify sensitive value and corresponding key of the secret.
              <br>
              <i>The key must be of type:
                <a
                  target="_blank"
                  href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
                >DNS
                  Subdomain</a></i>
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
                <p>
                  Please contact your
                  administrator and try again later.
                </p>
                <b>Error message:</b>
                <p>
                  <code class="ma-4">{{ errorMessage }}</code>
                </p>
              </v-container>
            </v-alert>
          </v-col>
        </v-row>
        <v-row justify="center">
          <v-col cols="6">
            <v-btn
              block
              variant="tonal"
              prepend-icon="mdi-lock"
              color="blue lighten-1"
              :disabled="errorMessage != ''"
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
                >apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: {{ secretName }}
  namespace: {{ namespaceName }}
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
        v-if="clipboardAvailable"
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
              variant="text"
              @click="copySealedSecret(counter)"
            >
              Copy to clipboard
            </v-btn>
            <v-spacer />
            <v-btn
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
            @click="displayCreateSealedSecretForm = !displayCreateSealedSecretForm"
          >
            Encrypt more secrets
          </v-btn>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script>
import { Base64 } from "js-base64";

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
    reader.readAsText(file);
  })
}

export default {
  name: "Secrets",
  data: function () {
    return {
      namespaces: [],
      scopes: ["strict", "cluster-wide", "namespace-wide"],
      errorMessage: "",
      hasErrorMessage: false,
      displayName: "",
      displayCreateSealedSecretForm: true,
      secretName: "",
      namespaceName: "",
      scope: "strict",
      secrets: [{ key: "", value: "", file: [] }],
      sealedSecrets: [],
      clipboardAvailable: false,
      rules: {
        validDnsSubdomain: [
          value => value.length < 253 || "Longer than 253 chars",
          value => !!value || 'Must not be empty',
          value => !!value && /^[a-z0-9-.]*$/.test(value) || 'Invalid char. Must be one of lower chars, digits, dashes or dots.',
          value => !!value && /^[a-z0-9]/.test(value) || 'Must start with a lower char or digit',
          value => !!value && /[a-z0-9]$/.test(value) || 'Must end with a lower char or digit',
          value => validDnsSubdomain(value) || "Not a valid DNS subdomain"
        ]
      },
      fileSize: [
        files => !files || !files.some(file => file.size > 1048576) || 'File size should be less than 1 MB!'
      ],
    };
  },
  computed: {
    hasNoSecrets: function () {
      if (this.secrets.length > 1) {
        return false;
      }
      let secret = this.secrets[0];
      return secret.key === '' && secret.value === '';
    },
    hasFile: function () {
      return this.secrets.map((e) => { return e.file.length > 0 })
    },
    hasValue: function () {
      return this.secrets.map((e) => { return e.value !== '' })
    },
    renderedSecrets: function () {
      return this.renderSecrets(this.sealedSecrets);
    }
  },
  beforeMount() {
    this.fetchNamespaces();
    this.fetchDisplayName();
  },
  mounted: function () {
    if (navigator && navigator.clipboard) {
      this.clipboardAvailable = true;
    }
    this.setErrorMessage("")
  },
  methods: {
    setErrorMessage(errorMessage) {
      this.errorMessage = errorMessage
      this.hasErrorMessage = !!errorMessage
    },
    fetchNamespaces: async function () {
      try {
        let response = await fetch("/config.json");
        let data = await response.json();
        let apiUrl = data["api_url"];

        response = await fetch(`${apiUrl}/namespaces`);
        this.namespaces = await response.json();
      } catch (error) {
        this.setErrorMessage(error)
      }
    },
    fetchDisplayName: async function () {
      let response = await fetch("/config.json");
      let data = await response.json();
      let dName = data["display_name"];
      this.displayName = dName;
    },
    fetchEncodedSecrets: async function () {
      try {
        var requestObject = {
          secret: this.secretName,
          namespace: this.namespaceName,
          scope: this.scope,
          secrets: await Promise.all(this.secrets.map(async (element) => {
            if (element.value) {
              return {
                key: element.key,
                value: Base64.encode(element.value),
              };
            } else {
              let fileContent = await readFileAsync(element.file[0])
              return {
                key: element.key,
                file: Base64.encode(fileContent)
              };
            }
          })),
        };

        let requestBody = JSON.stringify(requestObject, null, "\t");

        let response = await fetch("/config.json");
        let data = await response.json();
        let apiUrl = data["api_url"];

        response = await fetch(`${apiUrl}/secrets`, {
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
          this.sealedSecrets = await response.json();
          this.displayCreateSealedSecretForm = false;
        }
      } catch (error) {
        this.setErrorMessage(error)
      }
    },
    renderSecrets: function (sealedSecrets) {
      var dataEntries = sealedSecrets.map((element) => {
        return `    ${element["key"]}: ${element["value"]}`;
      });
      return "\n" + dataEntries.join("\n");
    },
    copyRenderedSecrets: function () {
      let sealedSecretElement = this.$refs.sealedSecret;
      console.log("sealedSecretElement: ", sealedSecretElement)
      let sealedSecretContent = sealedSecretElement.innerText.trim()
      navigator.clipboard.writeText(sealedSecretContent);
    },
    copySealedSecret: function (counter) {
      navigator.clipboard.writeText(this.sealedSecrets[counter].value)
    },
    removeSecret: function (counter) {
      if (this.secrets.length > 1) {
        this.secrets.splice(counter, 1)
      } else {
        this.secrets[0].key = '';
        this.secrets[0].value = '';
      }
    }
  },
};
</script>
<style>
.helper-info {
  margin-bottom: 10px;
}
</style>
