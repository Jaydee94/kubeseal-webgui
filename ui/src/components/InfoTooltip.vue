<template>
  <v-tooltip location="bottom" max-width="300" open-on-click>
    <template #activator="{ props: activatorProps }">
      <v-icon
        v-bind="mergeProps(activatorProps, $attrs)"
        icon="mdi-information-outline"
        size="small"
        color="medium-emphasis"
      />
    </template>
    <slot />
  </v-tooltip>
</template>

<script setup>
import { mergeProps } from 'vue'

// An info icon that explains a field in a tooltip (the default slot).
// Attributes such as `class` are applied to the icon.
defineOptions({ inheritAttrs: false })
</script>
