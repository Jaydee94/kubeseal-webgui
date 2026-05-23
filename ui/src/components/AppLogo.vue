<template>
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
  height: 48px;
  max-height: 100%;
  width: auto;
  object-fit: contain;
  margin: 0;
}

@media (min-width: 600px) {
  #logo-img {
    height: 56px;
  }
}
</style>