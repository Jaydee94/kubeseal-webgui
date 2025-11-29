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
        src="@/assets/logo-2025.png"
      >
    </a>
  </v-col>
</template>

<script>
export default {
  name: 'AppLogo'
}
</script>

<style scoped>
#logo {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  transition: all var(--transition-fast, 0.15s ease);
}

#logo-img {
  vertical-align: middle;
  transition: all var(--transition-fast, 0.15s ease);
  height: 200px;
  margin: 0;
}



/* Removed text styles */
</style>