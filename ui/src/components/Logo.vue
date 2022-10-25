<template>
  <v-col>
    <a
      id="logo"
      class="navbar-brand"
      href="#"
    >
      <img
        id="logo-img"
        alt="Kubeseal-Webgui Logo"
        :src="require('@/assets/logo.png')"
      >
      <span class="header-first">kubeseal</span>
      <span class="header-second">-webgui</span>
    </a>
  </v-col>
</template>

<script>
export default {
  name: 'Logo'
}
</script>

<style scoped>
#logo {
  text-decoration: none;
}

#logo-img {
  vertical-align: middle;
}

.header-first {
  color: #007bff;
  vertical-align: middle;
}

.header-second {
  color: orange;
  vertical-align: middle;
}

img {
  height: 40px;
  margin: 0 10px 0 0;
}

span {
  font-size: 1.5em;
}
</style>