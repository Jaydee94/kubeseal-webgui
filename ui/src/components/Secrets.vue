<template>
  <div class="secrets-component">
    <h3 align="center" v-if="displayName">{{ displayName }}</h3>
    <div class="secrets-form" v-if="displayCreateSealedSecretForm">
      <div align="right">
        <b-button variant="link" class="mb-2" id="help">
          <b-icon icon="question-circle" scale="1.5" />
        </b-button>
        <b-popover target="help" triggers="hover" placement="right">
          <template #title>Usage</template>
          <div align="left">
            The entered values will be encrypted using the <b>kubeseal</b> cli.
          </div>
          <div align="left">
            Kubeseal encrypts a plaintext secret using a configured public key.
          </div>
          <br />
          <div align="left">
            You can encrypt multiple <b>&lt;key&gt; &lt;value&gt;</b> pairs
            inside one
          </div>
          <div align="left">Kubernetes secret object.</div>
          <br />
          <div align="left">
            For more information about <b>sealed-secrets</b>
            <a
              target="_blank"
              href="https://github.com/bitnami-labs/sealed-secrets"
              >click here</a
            >.
          </div>
        </b-popover>
      </div>

      <b-form>
        <b-form-row class="mt-2">
          <b-col cols="4">
            <b-form-select
              v-model="namespaceName"
              :options="namespaces"
              :select-size="1"
              :state="namespaceNameState"
              :plain=true
            ></b-form-select>
            <b-form-text id="password-help-block">
              Select the target namespace where the sealed secret will be
              deployed.
            </b-form-text>
          </b-col>
          <b-col cols="4">
            <b-form-input
              v-model="secretName"
              placeholder="Secret name"
              id="input-secret-name"
              trim
              :state="secretNameState"
            ></b-form-input>
            <b-form-text id="password-help-block">
              Specify name of the secret.
              <br />
              <i
                >The secret name must be of type:
                <a
                  target="_blank"
                  href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
                  >DNS Subdomain</a
                ></i
              >
            </b-form-text>
          </b-col>
          <b-col cols="4">
            <b-form-select
              v-model="scope"
              :options="scopes"
              :select-size="1"
              :plain="true"
            ></b-form-select>
            <b-form-text id="scope-help-block">
              Specify scope of the secret.
              <br />
              <i
                >
                <a
                  target="_blank"
                  href="https://github.com/bitnami-labs/sealed-secrets#scopes"
                  >Scopes for sealed secrets</a
                ></i
              >
            </b-form-text>
          </b-col>
        </b-form-row>

        <div
          class="mt-4"
          v-for="(secret, counter) in secretsState"
          :key="counter"
        >
          <b-form-row class="align-items-center">
            <b-col cols="3">
              <b-form-textarea
                v-model="secret.key"
                placeholder="Secret key"
                id="input-key"
                :state="secret.state"
              ></b-form-textarea>
            </b-col>
            <b-col cols="8">
              <b-form-textarea
                rows="1"
                v-model="secret.value"
                :placeholder="'Secret value'"
                id="input-value"
              ></b-form-textarea>
            </b-col>
            <b-col cols="1">
              <b-button block variant="link"
                ><b-icon
                  icon="trash"
                  aria-hidden="true"
                  v-on:click="secrets.splice(counter, 1)"
                ></b-icon
              ></b-button>
            </b-col>
          </b-form-row>
        </div>
        <b-row>
          <b-col>
            <b-form-text block class="mb-3">
              Specify sensitive value and corresponding key of the secret.
              <br />
              <i
                >The key must be of type:
                <a
                  target="_blank"
                  href="https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#dns-subdomain-names"
                  >DNS Subdomain</a
                ></i
              >
            </b-form-text>
          </b-col>
        </b-row>
        <b-form-row>
          <b-col>
            <b-alert
              :show="!(!errorMessage || 0 === errorMessage.length)"
              dismissible
              variant="warning"
            >
              <p>
                Error while encoding sensitive data. Please contact your
                administrator and try again later.
              </p>
              <b>Error message: </b>
              <p class="mt-3">
                <code>{{ errorMessage }}</code>
              </p>
            </b-alert>
          </b-col>
        </b-form-row>
        <b-form-row class="mt-2">
          <b-col cols="6">
            <b-button
              block
              variant="secondary"
              v-on:click="secrets.push({ key: '', value: '' })"
              >Add key-value pair</b-button
            >
          </b-col>
          <b-col cols="6">
            <b-button block variant="primary" v-on:click="fetchEncodedSecrets()"
              >Encrypt</b-button
            >
          </b-col>
        </b-form-row>
      </b-form>
    </div>
    <div v-else>
      <b-row>
        <b-col>
          <div>
            <pre id="sealed-secret-result" ref="sealedSecret" class="px-3">
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
        </b-col>
      </b-row>
      <b-row>
        <b-col>
          <b-button
            block
            variant="link"
            class="mb-3"
            v-if="clipboardAvailable"
            v-on:click="copyRenderedSecrets()"
            >Copy <b-icon icon="clipboard-check" aria-hidden="true"></b-icon
          ></b-button>
          <b-button
            block
            variant="primary"
            :pressed.sync="displayCreateSealedSecretForm"
            >Encrypt more secrets
          </b-button>
        </b-col>
      </b-row>
    </div>
  </div>
</template>

<script>
import { Base64 } from "js-base64";
import "vue-popperjs/dist/vue-popper.css";

function validDnsSubdomain(name) {
  if (!name) {
    return;
  }
  var re = /^[a-z0-9]([a-z0-9._-]{0,251}[a-z0-9])?$/;
  return re.test(name);
}

export default {
  name: "Secrets",
  methods: {
    fetchNamespaces: async function () {
      try {
        let response = await fetch("/config.json");
        let data = await response.json();
        let apiUrl = data["api_url"];

        response = await fetch(`${apiUrl}/namespaces`);

        let availableNamespaces = await response.json();
        this.namespaces = JSON.parse(availableNamespaces);
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
          let sealedSecrets = await response.json();
          this.renderedSecrets = this.renderSecrets(sealedSecrets);
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
  },
  beforeMount() {
    this.fetchNamespaces();
    this.fetchDisplayName();
  },
  computed: {
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
  },
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
      renderedSecrets: "",
      clipboardAvailable: false,
    };
  },
  mounted: function() {
    if (navigator && navigator.clipboard) {
      this.clipboardAvailable = true;
    }
  },
};
</script>

<style scoped>
#sealed-secret-result {
  background: #eee;
}

html.dark #sealed-secret-result {
  background: #333;
}
</style>
