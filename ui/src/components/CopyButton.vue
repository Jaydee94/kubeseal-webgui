<template>
  <v-btn
    v-if="clipboardAvailable"
    icon
    :variant="copied ? 'flat' : 'text'"
    :color="copied ? 'success' : 'primary'"
    size="small"
    class="copy-btn"
    @click="copy"
  >
    <v-icon :icon="copied ? 'mdi-check' : 'mdi-content-copy'" />
    <v-tooltip activator="parent" location="bottom">{{ copied ? 'Copied!' : label }}</v-tooltip>
  </v-btn>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { COPIED_FEEDBACK_MS } from '@/constants'
import { copyToClipboard, isClipboardSupported } from '@/utils/clipboard'

const props = defineProps({
  // The text that is copied to the clipboard.
  text: {
    type: String,
    required: true
  },
  // Tooltip of the button while it is not showing "Copied!".
  label: {
    type: String,
    default: 'Copy to clipboard'
  }
})

const emit = defineEmits(['copied', 'copy-failed'])

const clipboardAvailable = isClipboardSupported()
const copied = ref(false)
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
