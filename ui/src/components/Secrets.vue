<template>
  <div class="secrets-component">
    <div class="secrets-form" v-if="displaySecretForm">
    <b-row>
        <b-col><p class="pre-form-text">Enter values for sealing:</p></b-col>
    </b-row>
    <b-form>
      <b-row class="secrets-form-row">
        <b-col>
          <b-form-input v-model="secretName" placeholder="secret name" id="input-secret-name"></b-form-input>
          <!-- <small class="form-text text-muted">secret name</small> -->
        </b-col>
      </b-row>
      <b-row class="secrets-form-row">
        <b-col>
          <b-form-input v-model="namespaceName" placeholder="namespace name" id="input-secret-name"></b-form-input> 
          <!-- <small class="form-text text-muted">namespace name</small> -->
        </b-col>
      </b-row>
      <b-card bg-variant="light" class="secrets-form-row" v-for="(secret, counter) in secrets" :key="counter">
        <b-row>
          <b-col cols="3">
            <b-form-textarea v-model="secret.key" placeholder="secret key" id="input-key"></b-form-textarea> 
          </b-col>
          <b-col cols="8">
            <b-form-textarea rows="1" v-model="secret.value" :placeholder="'secret value'" id="input-value"></b-form-textarea>
          </b-col>
          <b-col cols="1">
            <b-button variant="link"><b-icon icon="trash" aria-hidden="true" v-on:click="secrets.splice(counter, 1)"></b-icon></b-button>
          </b-col>
        </b-row>
      </b-card>
      <b-row class="secrets-form-row">
        <b-col>
          <b-button block variant="secondary" v-on:click="secrets.push({key: '', value: ''})">add key-value pair</b-button>
        </b-col>
      </b-row>
      <b-row class="secrets-form-row">
        <b-col><b-button block variant="primary" v-on:click="fetchEncodedSecrets()">encrypt</b-button></b-col>
      </b-row>
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
  .pre-form-text {
    font-weight: bold;
  }

  .secrets-form-row {
    margin-bottom: 20px;
  }

  #kubernetes-secret {
    margin-bottom: 20px;
  }
</style>
