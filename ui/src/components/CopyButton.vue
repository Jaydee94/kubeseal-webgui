<template>
  <template v-if="clipboardAvailable">
    <!-- With a caption the button is a text button... -->
    <v-btn
      v-if="caption"
      :prepend-icon="currentIcon"
      :variant="copied ? 'flat' : variant"
      :color="copied ? 'success' : 'primary'"
      size="small"
      class="copy-btn text-none result-action"
      :aria-label="copied ? undefined : accessibleName || undefined"
      @click="copy"
    >
      {{ copied ? 'Copied!' : caption }}
    </v-btn>
    <!-- ...without one an icon button that is named by its tooltip. -->
    <v-btn
      v-else
      icon
      :variant="copied ? 'flat' : 'text'"
      :color="copied ? 'success' : 'primary'"
      size="small"
      class="copy-btn"
      :aria-label="label"
      @click="copy"
    >
      <v-icon :icon="currentIcon" />
      <v-tooltip activator="parent" location="bottom">{{ copied ? 'Copied!' : label }}</v-tooltip>
    </v-btn>
  </template>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { COPIED_FEEDBACK_MS } from '@/constants'
import { copyToClipboard, isClipboardSupported } from '@/utils/clipboard'

const props = defineProps({
  // The text that is copied to the clipboard.
  text: {
    type: String,
    required: true
  },
  // Name of the icon-only button: its tooltip and accessible name.
  label: {
    type: String,
    default: 'Copy to clipboard'
  },
  // Name of a button with a caption, if the caption alone is ambiguous (it
  // must start with the caption, so that the visible label is in the name).
  accessibleName: {
    type: String,
    default: ''
  },
  // Turns the button into a text button with this text, e.g. "Copy".
  caption: {
    type: String,
    default: ''
  },
  // Style of a button with a caption.
  variant: {
    type: String,
    default: 'text'
  }
})

const emit = defineEmits(['copied', 'copy-failed'])

const clipboardAvailable = isClipboardSupported()
const copied = ref(false)
const currentIcon = computed(() => (copied.value ? 'mdi-check' : 'mdi-content-copy'))
let resetTimer = null

async function copy() {
  if (!(await copyToClipboard(props.text))) {
    emit('copy-failed')
    return
  }
  copied.value = true
  emit('copied')
  clearTimeout(resetTimer)
  resetTimer = setTimeout(() => {
    copied.value = false
  }, COPIED_FEEDBACK_MS)
}

onBeforeUnmount(() => clearTimeout(resetTimer))
</script>
