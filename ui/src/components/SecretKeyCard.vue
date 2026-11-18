<template>
  <v-card
    class="secret-key-card"
    :class="{ 'secret-key-card--expanded': expanded }"
    variant="flat"
    color="transparent"
  >
    <v-card-title class="d-flex align-center px-4 pt-3 pb-2">
      <v-icon size="18" class="mr-2 secret-key-card__icon">mdi-key-variant</v-icon>
      <!-- Long names are cut off (the full name is the tooltip) instead of
           pushing the button out of the card. -->
      <span class="secret-key-card__name" :title="secretKey">{{ secretKey }}</span>
      <v-spacer />
      <div class="flex-shrink-0 ml-2">
        <CopyButton
          :text="secretValue"
          caption="Copy"
          :accessible-name="`Copy ${secretKey}`"
          variant="outlined"
          @copied="$emit('copied')"
          @copy-failed="$emit('copy-failed')"
        />
      </div>
    </v-card-title>
    <!-- Explicit components instead of the card's text slot: the slot is
         rendered above the default slot, i.e. above the title. -->
    <v-card-text class="px-4 pb-3 pt-0">
      <!-- The whole value stays in the DOM (selecting and copying work on it);
           only its height is limited, with the last line fading out. -->
      <pre class="result-code"><code
        :id="valueId"
        ref="valueElement"
        class="secret-key-card__value"
        :class="{ 'secret-key-card__value--clamped': overflows && !expanded }"
      >{{ secretValue }}</code></pre>
      <div v-if="overflows" class="d-flex justify-end mt-1">
        <v-btn
          variant="text"
          size="small"
          density="comfortable"
          class="text-none secret-key-card__toggle"
          :prepend-icon="expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          :aria-expanded="expanded ? 'true' : 'false'"
          :aria-controls="valueId"
          :aria-label="`${expanded ? 'Show less' : 'Show all'} of ${secretKey}`"
          @click="expanded = !expanded"
        >
          {{ expanded ? 'Show less' : 'Show all' }}
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import CopyButton from './CopyButton.vue'

// Lines of the value shown before "Show all"; keep in step with `max-height` below.
const CLAMPED_LINES = 3

const props = defineProps({
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

const valueId = `secret-key-value-${useId()}`
const valueElement = ref(null)
const expanded = ref(false)
// Whether the value is longer than the clamp. Measured, because it depends on
// the width of the card: a value that fills three lines on a desktop needs
// five on a phone.
const overflows = ref(false)

function measure() {
  const element = valueElement.value
  if (!element) {
    return
  }
  // A line height of `normal` has no pixel value; 1.6em matches `.result-code`.
  const style = getComputedStyle(element)
  const parsed = parseFloat(style.lineHeight)
  const lineHeight = Number.isFinite(parsed) ? parsed : parseFloat(style.fontSize) * 1.6
  // The unclamped height is the scroll height whether or not it is clamped now;
  // the pixel of slack absorbs rounding.
  overflows.value = element.scrollHeight > lineHeight * CLAMPED_LINES + 1
  // A value that fits again (e.g. on a wider screen) has nothing left to expand.
  if (!overflows.value) {
    expanded.value = false
  }
}

let observer = null

onMounted(() => {
  measure()
  // The card is resized by the window and by the grid, not only by its content.
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(measure)
    observer.observe(valueElement.value)
  }
})

onBeforeUnmount(() => observer?.disconnect())

// The value can be replaced while the card stays (same position in the grid).
watch(
  () => props.secretValue,
  async () => {
    expanded.value = false
    await nextTick()
    measure()
  }
)
</script>

<style scoped>
/* A block (not inline) so that it can be limited in height. Size and line
   height are the block's own, so that the clamp and the measurement agree. */
.secret-key-card :deep(.result-code) {
  padding: 10px 14px;
  font-size: 0.75rem;
}

.secret-key-card__toggle {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.secret-key-card__value {
  display: block;
  font-size: inherit;
  line-height: inherit;
}

.secret-key-card__value--clamped {
  max-height: calc(3 * 1lh);
  overflow: hidden;
  /* The last line fades out: the text goes on, it is only not shown. */
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 1.6em), transparent);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 1.6em), transparent);
}

.secret-key-card__icon {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

.secret-key-card__name {
  min-width: 0;
  font-family: var(--font-mono);
  font-size: 0.875rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
