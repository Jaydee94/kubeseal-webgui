<template>
  <!-- The link carries the name; the image next to it is decoration. -->
  <a id="logo" href="/" aria-label="Kubeseal WebGui, start page">
    <img id="logo-img" alt="" src="@/assets/logo-2025.png" />
  </a>
</template>

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

@media (max-width: 599px) {
  #logo-img {
    height: 150px;
  }
}
</style>
