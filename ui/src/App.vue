<template>
  <div id="app">
    <b-container>
      <b-row id="logo">
        <b-col>
          <img alt="Kubeseal-Webgui Logo" src="./assets/kubeseal-webgui-logo.jpg">
        </b-col>
      </b-row>
      <Secrets />
    </b-container>
  </div>
</template>
<script>

// import HelloWorld from './components/HelloWorld.vue'
import './assets/custom.scss'

import Secrets from './components/Secrets.vue'

export default {
  name: 'App',
  components: {
    Secrets
  }
}
</script>

<style> 
#logo {
  text-align: center;
} 
</style>