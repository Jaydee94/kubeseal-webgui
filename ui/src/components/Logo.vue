<template>
  <a id="logo" class="navbar-brand" href="#">
    <img alt="Kubeseal-Webgui Logo" src="../assets/logo.png" class="align-middle">
    <span class="header-first align-middle">kubeseal</span>
    <span class="header-second align-middle">-webgui</span>
  </a>
</template>

<script>
export default {
  name: 'Logo'
}
</script>

<style scoped>
.header-first {
  color:#007bff;
}

.header-second {
  color:orange;
}
img {
  height: 40px;
  margin: 0 10px 0 0;
}

span {
  font-size: 1.5em;
}
</style>