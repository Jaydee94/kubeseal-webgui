<template>
  <div class="secrets-component">
    <div class="secrets-form" v-if="displaySecretForm">
    <b-row>
        <b-col>
          <p class="pre-form-text">Enter sensitive values for sealing in the form below. The cleartext values will be encrypted using the kubeseal-cli and displayed here afterwards.</p>
        </b-col>
    </b-row>
    <b-form>
      <b-form-row class="mt-2">
        <b-col cols="6">
          <b-form-input v-model="namespaceName" placeholder="Namespace name" id="input-secret-name"></b-form-input> 
          <b-form-text id="password-help-block">
            Specify the target namespace where the sealed secret will be deployed.
          </b-form-text>
        </b-col>
        <b-col cols="6">
          <b-form-input v-model="secretName" placeholder="Secret name" id="input-secret-name"></b-form-input>
          <b-form-text id="password-help-block">
            Specify the name of the secret.
          </b-form-text>
        </b-col>
      </b-form-row>
      <div bg-variant="light" class="mt-4" v-for="(secret, counter) in secrets" :key="counter">
        <b-form-row class="align-items-center">
          <b-col cols="3">
            <b-form-textarea v-model="secret.key" placeholder="Secret key" id="input-key"></b-form-textarea> 
          </b-col>
          <b-col cols="8">
            <b-form-textarea rows="1" v-model="secret.value" :placeholder="'Secret value'" id="input-value"></b-form-textarea>
          </b-col>
          <b-col cols="1">
            <b-button block variant="link"><b-icon icon="trash" font-scale="1.5" aria-hidden="true" v-on:click="secrets.splice(counter, 1)"></b-icon></b-button>
          </b-col>
        </b-form-row>
      </div>
      <b-form-row>
        <b-form-text id="password-help-block" class="mb-3">
          Specify sensitive value and corresponding key of the secret.
        </b-form-text>
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
      <b-card bg-variant="light" title="kubernetes secret" id="kubernetes-secret">
        <pre><code>{{ sealedSecret }}</code></pre>
        <b-button variant="link">copy <b-icon icon="clipboard-check" aria-hidden="true"></b-icon></b-button>
      </b-card>
      <b-button block variant="primary" :pressed.sync="displaySecretForm">encrypt another secret </b-button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Secrets',
  methods: {
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

        let sealedSecrets = await response.json();
        
        this.sealedSecret = sealedSecrets
        this.displaySecretForm = false;
      } catch(error) {
        console.log(error)
      }
    }
  },
  data: function() {
    return {
      displaySecretForm: true,
      secretName: "",
      namespaceName: "",
      secrets: [
        { key: "", value: "" }
      ],
      sealedSecret: "blubb"
    }
  }
}
</script>

<style scoped>
</style>
