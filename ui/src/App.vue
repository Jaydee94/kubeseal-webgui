<template>
  <div id="app">
    <b-container>
      <b-row id="logo"><b-col><img alt="Vue logo" src="./assets/kubeseal-webgui-logo.jpg"></b-col></b-row>
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
#app { 
  margin-top: 60px;
}

#logo img {
  text-align: center;
}
</style>