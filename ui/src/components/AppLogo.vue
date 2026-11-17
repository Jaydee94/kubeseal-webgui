<template>
  <!-- The link carries the name; the image next to it is decoration. -->
  <a id="logo" href="/" aria-label="Kubeseal WebGui, start page">
    <img id="logo-img" alt="" :src="dark ? logoDark : logoLight" />
  </a>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import logoLight from '@/assets/logo-2025.png'
// The navy lettering of the light logo is hardly readable on the dark bar, so
// the dark theme has a variant with light lettering (lock and orange unchanged).
import logoDark from '@/assets/logo-2025-dark.png'

const theme = useTheme()
const dark = computed(() => theme.current.value.dark)
</script>

<style scoped>
#logo {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  border-radius: 6px;
  transition: opacity var(--transition-fast, 0.15s ease);
}

#logo:hover {
  opacity: 0.85;
}

#logo:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 4px;
}

#logo-img {
  vertical-align: middle;
  transition: all var(--transition-fast, 0.15s ease);
  /* The image is cropped to the artwork, so this is the visible height. */
  height: 38px;
  width: auto;
  margin: 0;
}
</style>
