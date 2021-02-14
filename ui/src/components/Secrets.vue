<template>
  <div class="secrets-component">
    <h2 align="center" v-if="displayName">{{ displayName }}</h2>
    <div class="secrets-form" v-if="displayCreateSealedSecretForm">
    <b-row>
        <b-col class="mb-3">
            Enter sensitive values for sealing in the form below. The cleartext values will be encrypted using the kubeseal-cli and displayed here afterwards.
        </b-col>
    </b-row>

    <b-form>
      <b-form-row class="mt-2">
        <b-col cols="6">
          <b-form-select v-model="namespaceName" :options="namespaces" :select-size="1"></b-form-select>
          <b-form-text id="password-help-block">
            Specify target namespace where the sealed secret will be deployed.
          </b-form-text>
        </b-col>
        <b-col cols="6">
          <b-form-input v-model="secretName" placeholder="Secret name" id="input-secret-name"></b-form-input>
          <b-form-text id="password-help-block">
            Specify name of the secret.
          </b-form-text>
        </b-col>
      </b-form-row>

      <div class="mt-4" v-for="(secret, counter) in secrets" :key="counter">
        <b-form-row class="align-items-center">
          <b-col cols="3">
            <b-form-textarea v-model="secret.key" placeholder="Secret key" id="input-key"></b-form-textarea> 
          </b-col>
          <b-col cols="8">
            <b-form-textarea rows="1" v-model="secret.value" :placeholder="'Secret value'" id="input-value"></b-form-textarea>
          </b-col>
          <b-col cols="1">
            <b-button block variant="link"><b-icon icon="trash" aria-hidden="true" v-on:click="secrets.splice(counter, 1)"></b-icon></b-button>
          </b-col>
        </b-form-row>
      </div>
      <b-row>
        <b-col>
          <b-form-text block class="mb-3">
            Specify sensitive value and corresponding key of the secret.
          </b-form-text>
        </b-col>
      </b-row>
      <b-form-row>
        <b-col>
          <b-alert :show="!(!errorMessage || 0 === errorMessage.length)" dismissible variant="warning">
            <p>Error while encoding sensitive data. Please contact your administrator and try again later.</p>
            <b>Error message: </b>
            <p class="mt-3"><code>{{errorMessage}}</code></p>
          </b-alert>
        </b-col>
      </b-form-row>
      <b-form-row class="mt-2">
        <b-col cols="6">
          <b-button block variant="secondary" v-on:click="secrets.push({key: '', value: ''})">Add key-value pair</b-button>
        </b-col>
        <b-col cols="6">
          <b-button block variant="primary" v-on:click="fetchEncodedSecrets()">Encrypt</b-button>
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
          <b-button block variant="link" class="mb-3" v-on:click="copyRenderedSecrets()">Copy <b-icon icon="clipboard-check" aria-hidden="true"></b-icon></b-button>
          <b-button block variant="primary" :pressed.sync="displayCreateSealedSecretForm">Encrypt more secrets </b-button>
        </b-col>
      </b-row>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Secrets',
  methods: {
    fetchNamespaces: async function() {
      try {
        let response = await fetch('/config.json');
        let data = await response.json();
        let apiUrl = data["api_url"];
        
        response = await fetch(`${apiUrl}/namespaces`);

        let availableNamespaces = await response.json();
        this.namespaces = JSON.parse(availableNamespaces);
      } catch(error) {
        this.errorMessage = error;
      }
    },
    fetchDisplayName: async function() {
      let response = await fetch('/config.json');
      let data = await response.json();
      let dName = data["display_name"];
      this.displayName = dName;
    },
    fetchEncodedSecrets: async function() {
      try {
        var requestObject = {
          secret: this.secretName,
          namespace: this.namespaceName,
          secrets: []
        }

        this.secrets.forEach(element => {
          requestObject.secrets.push({key: element.key, value: btoa(element.value)})
        });

        let requestBody = JSON.stringify(requestObject, null, '\t')

        let response = await fetch('/config.json');
        let data = await response.json();
        let apiUrl = data["api_url"];
        
        response = await fetch(`${apiUrl}/secrets`, {
          method: 'POST',
          headers: {
            // 'Origin': 'http://localhost:8080',
            'Content-Type': 'application/json'
          },
          body: requestBody
        });

        let sealedSecrets = await response.json()
        this.renderedSecrets = this.renderSecrets(sealedSecrets)
        this.displayCreateSealedSecretForm = false;
      } catch(error) {
        this.errorMessage = error;
      }
    },
    renderSecrets: function(sealedSecrets) {
      var dataEntries = [];
      sealedSecrets.forEach(element => {
        let entry = `    ${element['key']}: ${element['value']}`
        dataEntries.push(entry);
      });
      return dataEntries.join("\n");
    },
    copyRenderedSecrets: function() {
      let sealedSecretElement = this.$refs["sealedSecret"]
      let sealedSecretContent = sealedSecretElement.innerText.trim()
      navigator.clipboard.writeText(sealedSecretContent)
    }
  },
  beforeMount(){
    this.fetchNamespaces()
    this.fetchDisplayName()
  },
  data: function() {
    return {
      namespaces: [],
      errorMessage: "",
      displayName: "",
      displayCreateSealedSecretForm: true,
      secretName: "",
      namespaceName: "",
      secrets: [
        { key: "", value: "" }
      ],
      renderedSecrets: ""
    }
  }
}
</script>

<style scoped>
#sealed-secret-result {
  background: #eeeeee;
}

</style>
