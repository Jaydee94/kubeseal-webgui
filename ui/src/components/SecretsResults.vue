<template>
  <div class="secrets-results">
    <SealedSecretCard
      :manifest="manifest"
      :secret-name="secretName"
      :namespace="namespace"
      :scope="scope"
      :cluster="cluster"
      :key-count="sealedSecrets.length"
      @copied="$emit('copied', $event)"
      @copy-failed="$emit('copy-failed', $event)"
      @downloaded="$emit('downloaded', $event)"
    />
    <!-- The sealed value of each key on its own, e.g. to patch a manifest
         that already exists. -->
    <section class="panel keys-panel mt-3" aria-labelledby="keysTitle">
      <div class="panel__header px-5 pt-4 pb-1">
        <h2 id="keysTitle" class="panel__title">Sealed values</h2>
        <span class="count-badge" aria-hidden="true">{{ sealedSecrets.length }}</span>
      </div>
      <div class="key-cards">
        <SecretKeyCard
          v-for="secret in sealedSecrets"
          :key="secret.key"
          class="key-cards__card"
          :secret-key="secret.key"
          :secret-value="secret.value"
          @copied="$emit('copied', keyCopiedMessage(secret.key))"
          @copy-failed="$emit('copy-failed', 'Failed to copy secret value to clipboard.')"
        />
      </div>
    </section>
    <div class="panel result-nav mt-3">
      <v-btn
        variant="text"
        prepend-icon="mdi-pencil-outline"
        class="btn-ghost result-action"
        @click="$emit('edit')"
      >
        Edit Secrets
      </v-btn>
      <v-btn
        variant="text"
        prepend-icon="mdi-plus"
        class="btn-ghost result-action"
        @click="$emit('clear')"
      >
        Clear
      </v-btn>
    </div>
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
  },
  // What was sealed, for the summary and the name of the download.
  secretName: {
    type: String,
    default: ''
  },
  namespace: {
    type: String,
    default: ''
  },
  scope: {
    type: String,
    required: true
  },
  // The cluster that sealed the values, or empty for a single cluster.
  cluster: {
    type: String,
    default: ''
  }
})

// `copied`, `copy-failed` and `downloaded` carry the message to show.
defineEmits(['copied', 'copy-failed', 'downloaded', 'clear', 'edit'])

function keyCopiedMessage(key) {
  return `Secret key "${key}" copied to clipboard!`
}
</script>

<style scoped>
/* One list of rows, separated by hairlines. */
.key-cards {
  display: flex;
  flex-direction: column;
  padding: 0 4px 4px;
}

.key-cards__card + .key-cards__card {
  border-top: 1px solid var(--line) !important;
  border-radius: 0 !important;
}

/* Back to the form on the left, start over on the right. */
.result-nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
}
</style>
