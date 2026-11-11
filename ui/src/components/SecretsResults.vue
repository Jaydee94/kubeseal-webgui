<template>
  <div>
    <v-row>
      <v-col>
        <SealedSecretCard
          :manifest="manifest"
          @copied="$emit('copied', 'Sealed secret copied to clipboard!')"
          @copy-failed="$emit('copy-failed', 'Failed to copy sealed secret to clipboard.')"
        />
      </v-col>
    </v-row>
    <v-row dense align-content="center" class="mt-4">
      <v-col v-for="(secret, counter) in sealedSecrets" :key="counter" cols="12" sm="6" md="4">
        <SecretKeyCard
          :secret-key="secret.key"
          :secret-value="secret.value"
          @copied="$emit('copied', keyCopiedMessage(secret.key))"
          @copy-failed="$emit('copy-failed', 'Failed to copy secret value to clipboard.')"
        />
      </v-col>
    </v-row>
    <v-row justify="center" class="mt-4">
      <v-col cols="12" sm="6" md="4" class="d-flex justify-center ga-3">
        <v-btn variant="outlined" color="primary" @click="$emit('clear')"> Clear </v-btn>
        <v-btn variant="outlined" color="secondary" @click="$emit('edit')"> Edit Secrets </v-btn>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import SealedSecretCard from './SealedSecretCard.vue'
import SecretKeyCard from './SecretKeyCard.vue'

defineProps({
  // The sealed values as returned by the API: [{ key, value }, ...].
  sealedSecrets: {
    type: Array,
    required: true
  },
  // The complete SealedSecret manifest as YAML text.
  manifest: {
    type: String,
    required: true
  }
})

// `copied` and `copy-failed` carry the message to show to the user.
defineEmits(['copied', 'copy-failed', 'clear', 'edit'])

function keyCopiedMessage(key) {
  return `Secret key "${key}" copied to clipboard!`
}
</script>
