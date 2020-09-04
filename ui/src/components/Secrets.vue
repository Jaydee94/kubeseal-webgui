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
        <b-col><b-button block variant="primary" :pressed.sync="displaySecretForm">encrypt</b-button></b-col>
      </b-row>
    </b-form>
    </div>
    <div v-else>
      <b-card bg-variant="light" title="kubernetes secret" id="kubernetes-secret">
        <pre><code>{{ decodeSealedSecret() }}</code></pre>
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
    decodeSealedSecret: function() {
      return atob(this.sealedSecret)
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
      sealedSecret: "YXBpVmVyc2lvbjogYml0bmFtaS5jb20vdjFhbHBoYTEKa2luZDogU2VhbGVkU2VjcmV0Cm1ldGFkYXRhOgogIG5hbWU6IG15c2VjcmV0CiAgbmFtZXNwYWNlOiBteW5hbWVzcGFjZQogIGFubm90YXRpb246CiAgICAia3ViZWN0bC5rdWJlcm5ldGVzLmlvL2xhc3QtYXBwbGllZC1jb25maWd1cmF0aW9uIjogLi4uLgpzcGVjOgogIGVuY3J5cHRlZERhdGE6CiAgICAuZG9ja2VyY2ZnOiBBZ0J5M2k0T0pTV0srUGlUeVNZWlpBOXJPNDNjR0RFcS4uLi4uCiAgdGVtcGxhdGU6CiAgICB0eXBlOiBrdWJlcm5ldGVzLmlvL2RvY2tlcmNmZwogICAgIyB0aGlzIGlzIGFuIGV4YW1wbGUgb2YgbGFiZWxzIGFuZCBhbm5vdGF0aW9ucyB0aGF0IHdpbGwgYmUgYWRkZWQgdG8gdGhlIG91dHB1dCBzZWNyZXQKICAgIG1ldGFkYXRhOgogICAgICBsYWJlbHM6CiAgICAgICAgImplbmtpbnMuaW8vY3JlZGVudGlhbHMtdHlwZSI6IHVzZXJuYW1lUGFzc3dvcmQKICAgICAgYW5ub3RhdGlvbnM6CiAgICAgICAgImplbmtpbnMuaW8vY3JlZGVudGlhbHMtZGVzY3JpcHRpb24iOiBjcmVkZW50aWFscyBmcm9tIEt1YmVybmV0ZXM="
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
