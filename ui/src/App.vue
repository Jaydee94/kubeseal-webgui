<template>
  <div id="app">
    <b-container>
      <b-row id="logo">
        <b-col>
          <img alt="Kubeseal-Webgui Logo" src="./assets/kubeseal-webgui-logo.jpg">
          <h3 v-if="instanceName">{{ instanceName | uppercase }}</h3>
          <br>
        </b-col>
      </b-row>
      <Secrets />
    </b-container>
  </div>
</template>
<script>

import './assets/custom.scss'
import Secrets from './components/Secrets.vue'
import axios from 'axios';

export default {
  name: 'App',
  components: {
    Secrets
  },
  data: function () {
    return{
      instanceName: ""
    }
  },
  mounted() {
    axios.get("http://localhost:5000/appconfig" , {
            headers: {
            'Content-Type': 'application/json'
            }
        })
        .then(response => {
            this.instanceName = response.data.INSTANCE_NAME
        })
       .catch(function (error) {
             console.log(error);
        });
  }
}
</script>

<style> 
#logo {
  text-align: center;
},
h3 {
  font-family: Georgia;
}
</style>