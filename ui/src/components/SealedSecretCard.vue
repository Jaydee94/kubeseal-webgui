<template>
  <v-card class="ma-1 modern-card result-card" elevation="1" variant="outlined">
    <v-card-title class="d-flex align-center justify-space-between px-4 py-3">
      <div class="d-flex align-center">
        <v-icon class="mr-2" color="success" size="small">mdi-check-circle</v-icon>
        <span class="text-h6 font-weight-medium">Generated Sealed Secret</span>
      </div>
    </v-card-title>
    <!-- Explicit components instead of the card's text/actions slots: the
         slots are rendered above the default slot, i.e. above the title. -->
    <v-card-text>
      <pre
        class="overflow-auto result-code"
      ><code id="sealed-secret-result" class="overflow-auto">{{ manifest }}</code></pre>
    </v-card-text>
    <v-card-actions>
      <CopyButton :text="manifest" @copied="$emit('copied')" @copy-failed="$emit('copy-failed')" />
    </v-card-actions>
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
