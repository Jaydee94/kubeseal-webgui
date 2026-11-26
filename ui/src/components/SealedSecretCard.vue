<template>
  <v-card class="panel result-card" variant="flat">
    <v-card-title class="result-card__header d-flex flex-wrap align-center px-5 pt-4 pb-3 ga-3">
      <div class="d-flex align-center mr-auto ga-3 result-card__heading">
        <span class="result-card__badge" aria-hidden="true">
          <v-icon size="18" icon="mdi-shield-lock-outline" />
        </span>
        <!-- Receives the focus when the result appears. -->
        <span class="result-card__title" tabindex="-1">Generated Sealed Secret</span>
      </div>
      <div class="result-card__actions d-flex flex-wrap align-center ga-2">
        <CopyButton
          :text="manifest"
          caption="Copy"
          accessible-name="Copy manifest"
          variant="outlined"
          @copied="$emit('copied', 'Sealed secret copied to clipboard!')"
          @copy-failed="$emit('copy-failed', 'Failed to copy sealed secret to clipboard.')"
        />
        <v-btn
          prepend-icon="mdi-download"
          variant="flat"
          color="primary"
          size="small"
          class="result-action"
          @click="download"
        >
          Download .yaml
        </v-btn>
      </div>
    </v-card-title>
    <!-- Explicit components instead of the card's text/actions slots: the
         slots are rendered above the default slot, i.e. above the title. -->
    <v-card-text class="px-5 pb-5">
      <div class="result-summary d-flex flex-wrap ga-2 mb-3" role="group" aria-label="Summary">
        <v-chip
          v-for="chip in chips"
          :key="chip.icon"
          :prepend-icon="chip.icon"
          size="small"
          variant="outlined"
          class="summary-chip"
          label
        >
          {{ chip.text }}
        </v-chip>
      </div>
      <pre class="result-code"><YamlCode id="sealed-secret-result" :text="manifest" /></pre>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { SCOPE_CLUSTER_WIDE } from '@/constants'
import { downloadTextFile } from '@/utils/download'
import { manifestFileName } from '@/utils/sealedSecretYaml'
import CopyButton from './CopyButton.vue'
import YamlCode from './YamlCode'

const props = defineProps({
  // The complete SealedSecret manifest as YAML text.
  manifest: {
    type: String,
    required: true
  },
  // What the manifest was sealed for, for its summary and the file name.
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
  keyCount: {
    type: Number,
    required: true
  },
  // The cluster whose certificate sealed the secret. Empty for a single
  // cluster, where there is nothing to tell apart.
  cluster: {
    type: String,
    default: ''
  }
})

// `copied`, `copy-failed` and `downloaded` carry the message to show.
const emit = defineEmits(['copied', 'copy-failed', 'downloaded'])

// A cluster-wide secret has no namespace, and its scope says it all.
const chips = computed(() => {
  const keys = {
    icon: 'mdi-key-variant',
    text: `${props.keyCount} ${props.keyCount === 1 ? 'key' : 'keys'}`
  }
  const cluster = props.cluster ? [{ icon: 'mdi-server', text: props.cluster }] : []
  if (props.scope === SCOPE_CLUSTER_WIDE) {
    return [keys, ...cluster, { icon: 'mdi-shield-lock-outline', text: SCOPE_CLUSTER_WIDE }]
  }
  return [
    keys,
    ...cluster,
    { icon: 'mdi-folder-outline', text: props.namespace },
    { icon: 'mdi-shield-lock-outline', text: `${props.scope} scope` }
  ]
})

function download() {
  const fileName = manifestFileName(props.secretName)
  downloadTextFile(fileName, props.manifest)
  emit('downloaded', `Downloaded ${fileName}`)
}
</script>

<style scoped>
.result-card__heading {
  min-width: 0;
}

/* A tinted tile with the icon, the visual anchor of the result. */
.result-card__badge {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: rgba(var(--v-theme-success), 0.14);
  color: rgb(var(--v-theme-success));
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-success), 0.25);
}

.result-card__title {
  font-size: 1.0625rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  outline: none;
}

.summary-chip {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  border-color: var(--line-strong);
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
</style>
