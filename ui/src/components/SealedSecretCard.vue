<template>
  <v-card class="ma-1 modern-card result-card" elevation="1" variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between px-4 py-3">
      <div class="d-flex align-center">
        <v-icon class="mr-2" color="success" size="small">mdi-check-circle</v-icon>
        <span class="text-h6 font-weight-medium">Generated Sealed Secret</span>
      </div>
    </v-card-title>
    <template #text>
      <pre
        class="overflow-auto result-code"
      ><code id="sealed-secret-result" class="overflow-auto">{{ manifest }}</code></pre>
    </template>
    <template #actions>
      <CopyButton :text="manifest" @copied="$emit('copied')" @copy-failed="$emit('copy-failed')" />
    </template>
  </v-card>
</template>

<script setup>
import CopyButton from './CopyButton.vue'

defineProps({
  // The complete SealedSecret manifest as YAML text.
  manifest: {
    type: String,
    required: true
  }
})

defineEmits(['copied', 'copy-failed'])
</script>
