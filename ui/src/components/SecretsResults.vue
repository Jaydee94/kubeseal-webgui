<template>
  <div class="secrets-results">
    <!-- One manifest, with the sealed value of each key on its own (e.g. to
         patch a manifest that already exists), for every namespace sealed for. -->
    <template v-for="(result, index) in results" :key="result.namespace">
      <SealedSecretCard
        :class="{ 'mt-3': index > 0 }"
        :manifest="result.manifest"
        :secret-name="secretName"
        :namespace="result.namespace"
        :scope="scope"
        :cluster="cluster"
        :key-count="result.entries.length"
        :result-id="index === 0 ? 'sealed-secret-result' : `sealed-secret-result-${index + 1}`"
        :label="results.length > 1 ? result.namespace : ''"
        @copied="$emit('copied', $event)"
        @copy-failed="$emit('copy-failed', $event)"
        @downloaded="$emit('downloaded', $event)"
      />
      <section class="panel keys-panel mt-3" :aria-labelledby="`keysTitle-${index}`">
        <div class="panel__header px-5 pt-4 pb-1">
          <h2 :id="`keysTitle-${index}`" class="panel__title">
            Sealed values<template v-if="results.length > 1"> · {{ result.namespace }}</template>
          </h2>
          <span class="count-badge" aria-hidden="true">{{ result.entries.length }}</span>
        </div>
        <div class="key-cards">
          <SecretKeyCard
            v-for="secret in result.entries"
            :key="secret.key"
            class="key-cards__card"
            :secret-key="secret.key"
            :secret-value="secret.value"
            @copied="$emit('copied', keyCopiedMessage(secret.key))"
            @copy-failed="$emit('copy-failed', 'Failed to copy secret value to clipboard.')"
          />
        </div>
      </section>
    </template>
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
  // What was sealed, one entry per namespace:
  // [{ namespace, entries: [{ key, value }, ...], manifest }, ...]. `entries`
  // are the sealed values as returned by the API, `manifest` the complete
  // SealedSecret as YAML text.
  results: {
    type: Array,
    required: true
  },
  // What was sealed, for the summary and the name of the download.
  secretName: {
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
