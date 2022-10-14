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
      <div align="right">
        <v-btn
          id="help"
          variant="text"
        >
          <v-icon
            large
            aria-hidden="true"
          >
            mdi-question-mark
          </v-icon>
        </v-btn>
        <v-tooltip
          target="help"
          triggers="hover"
          placement="right"
        >
          <template #title>
            Usage
          </template>
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
      </div>

      <v-form>
        <v-row class="mt-2">
          <v-col cols="4">
            <v-autocomplete
              v-model="namespaceName"
              :items="namespaces"
              :state="namespaceNameState"
              hint="Namespace name"
            />
            <v-container id="password-help-block">
              Select the target namespace where the sealed secret will be
              deployed.
            </v-container>
          </v-col>
          <v-col cols="4">
            <v-text-field
              id="input-secret-name"
              v-model="secretName"
              hint="Secret name"
              trim
              :state="secretNameState"
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
          <v-col cols="4">
            <v-select
              v-model="scope"
              :items="scopes"
              :select-size="1"
              :plain="true"
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

        <div
          v-for="(secret, counter) in secretsState"
          :key="counter"
          class="mt-4"
        >
          <v-row class="align-items-center">
            <v-col cols="3">
              <v-textarea
                id="input-key"
                v-model="secret.key"
                placeholder="Secret key"
                :state="secret.state"
              />
            </v-col>
            <v-col cols="8">
              <v-textarea
                id="input-value"
                v-model="secret.value"
                rows="1"
                :placeholder="'Secret value'"
              />
            </v-col>
            <v-col cols="1">
              <v-btn
                block
                variant="text"
                :disabled="hasNoSecrets"
              >
                <v-icon
                  aria-hidden="true"
                  class="ma-2"
                  @click="removeSecret(counter)"
                >
                  mdi-delete
                </v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </div>
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
              type="warning"
              icon="mdi-flash"
            >
              <p>
                Error while encoding sensitive data. Please contact your
                administrator and try again later.
              </p>
              <b>Error message: </b>
              <p class="mt-3">
                <code>{{ errorMessage }}</code>
              </p>
            </v-alert>
          </v-col>
        </v-row>
        <v-row class="mt-2">
          <v-col cols="6">
            <v-btn
              block
              color="secondary"
              @click="secrets.push({ key: '', value: '' })"
            >
              Add key-value pair
            </v-btn>
          </v-col>
          <v-col cols="6">
            <v-btn
              block
              variant="tonal"
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
          <div>
            <pre
              id="sealed-secret-result"
              ref="sealedSecret"
              class="px-3"
            >
              <code>
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: {{ secretName }}
  namespace: {{ namespaceName }}
spec:
  encryptedData:
{{ renderedSecrets }}</code>
            </pre>
          </div>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="d-flex justify-content-center">
          <v-btn
            v-if="clipboardAvailable"
            block
            variant="text"
            @click="copyRenderedSecrets()"
          >
            Copy complete secret
            <v-icon aria-hidden="true">
              mdi-copy-content
            </v-icon>
          </v-btn>
        </v-col>
      </v-row>
      <v-row
        v-if="clipboardAvailable"
        class="d-flex"
      >
        <v-col
          v-for="(secret, counter) in sealedSecrets"
          :key="counter"
          class="flex"
        >
          <v-btn
            variant="text"
            @click="copySealedSecret(counter)"
          >
            Copy
            <v-icon aria-hidden="true">
              mdi-content-copy
            </v-icon>
            : <code>{{ secret["key"] }}</code>
          </v-btn>
        </v-col>
      </v-row>
      <v-row>
        <v-col class="d-flex">
          <v-btn
            block
            variant="tonal"
            class="flex-fill"
            @click="displayCreateSealedSecretForm=!displayCreateSealedSecretForm"
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

export default {
  name: "Secrets",
  data: function () {
    return {
      namespaces: [],
      scopes: ["strict", "cluster-wide", "namespace-wide"],
      errorMessage: "",
      displayName: "",
      displayCreateSealedSecretForm: true,
      secretName: "",
      namespaceName: "",
      scope: "strict",
      secrets: [{ key: "", value: "" }],
      sealedSecrets: [],
      clipboardAvailable: false,
    };
  },
  computed: {
    hasErrorMessage: function () {
      return !(!this.errorMessage || 0 === this.errorMessage.length)
    },
    secretNameState: function () {
      return validDnsSubdomain(this.secretName);
    },
    namespaceNameState: function () {
      return validDnsSubdomain(this.namespaceName);
    },
    secretsState: function () {
      return this.secrets.map((e) => {
        e.state = validDnsSubdomain(e.key);
        return e;
      });
    },
    hasNoSecrets: function () {
      if (this.secrets.length > 1) {
        return false;
      }
      let secret = this.secrets[0];
      return secret.key === '' && secret.value === '';
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
  },
  methods: {
    fetchNamespaces: async function () {
      try {
        let response = await fetch("/config.json");
        let data = await response.json();
        let apiUrl = data["api_url"];

        response = await fetch(`${apiUrl}/namespaces`);
        this.namespaces = await response.json();
      } catch (error) {
        this.errorMessage = error;
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
          secrets: this.secrets.map((element) => {
            return {
              key: element.key,
              value: Base64.encode(element.value),
            };
          }),
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
        this.errorMessage = error;
      }
    },
    renderSecrets: function (sealedSecrets) {
      var dataEntries = sealedSecrets.map((element) => {
        return `    ${element["key"]}: ${element["value"]}`;
      });
      return dataEntries.join("\n");
    },
    copyRenderedSecrets: function () {
      let sealedSecretElement = this.$refs["sealedSecret"];
      let sealedSecretContent = sealedSecretElement.innerText.trim();
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
