<template>
  <v-card class="modern-card secret-key-card" elevation="1" variant="outlined">
    <v-card-title class="d-flex align-center px-4 py-3">
      <v-icon size="small" class="mr-2" color="primary">mdi-key-variant</v-icon>
      <span class="text-subtitle-1 font-weight-medium">{{ secretKey }}</span>
    </v-card-title>
    <!-- Explicit components instead of the card's text/actions slots: the
         slots are rendered above the default slot, i.e. above the title. -->
    <v-card-text>
      <pre
        class="overflow-auto result-code"
      ><code class="overflow-auto">{{ secretValue }}</code></pre>
    </v-card-text>
    <v-card-actions>
      <CopyButton
        :text="secretValue"
        label="Copy value"
        @copied="$emit('copied')"
        @copy-failed="$emit('copy-failed')"
      />
    </v-card-actions>
  </v-card>
</template>

<script setup>
import CopyButton from './CopyButton.vue'

defineProps({
  secretKey: {
    type: String,
    required: true
  },
  // The sealed value of the key.
  secretValue: {
    type: String,
    required: true
  }
})

defineEmits(['copied', 'copy-failed'])
</script>
