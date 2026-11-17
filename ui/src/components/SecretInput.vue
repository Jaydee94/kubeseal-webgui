<template>
  <!-- One grid for the pair: key | value | remove on wider screens, a bordered
       card with the number and remove button as its header below 600px. The
       columns are fixed, so typing a value or choosing a file never moves them.
       The DOM order is the tab order; `grid-template-areas` sets the layout. -->
  <div class="secret-row" role="group" :aria-label="`Pair ${number}`">
    <span class="secret-row__number text-caption text-medium-emphasis" aria-hidden="true">
      #{{ number }}
    </span>

    <v-text-field
      :id="`secretKey-${index}`"
      ref="keyField"
      :model-value="entry.key"
      label="Secret key"
      density="comfortable"
      autocomplete="off"
      spellcheck="false"
      clearable
      variant="outlined"
      class="secret-row__key modern-input"
      color="primary"
      :rules="rules.validSecretKey"
      :error-messages="duplicate ? [DUPLICATE_KEY_MESSAGE] : []"
      @update:model-value="$emit('update:key', $event ?? '')"
    />

    <div class="secret-row__value">
      <!-- The file replaces the text area visually, in the same column. -->
      <div v-if="hasFile" :id="`secretFile-${index}`" class="secret-file">
        <v-chip
          closable
          label
          size="large"
          prepend-icon="mdi-file-document-outline"
          close-label="Remove file"
          class="secret-file__chip"
          @click:close="$emit('update:file', null)"
        >
          <span class="secret-file__name">{{ entry.file.name }}</span>
          <span class="secret-file__size text-medium-emphasis ml-2">
            {{ formatFileSize(entry.file.size) }}
          </span>
        </v-chip>
      </div>
      <v-textarea
        v-else
        :id="`secretValue-${index}`"
        :model-value="entry.value"
        rows="1"
        auto-grow
        autocomplete="off"
        spellcheck="false"
        label="Secret value"
        density="comfortable"
        variant="outlined"
        color="primary"
        class="secret-row__textarea modern-input"
        :class="{ 'secret-value--masked': !revealed }"
        :rules="valueRules"
        :error-messages="entry.fileError"
        @update:model-value="$emit('update:value', $event ?? '')"
      >
        <template #append-inner>
          <v-btn
            icon
            variant="text"
            size="small"
            density="comfortable"
            aria-label="Show value"
            :aria-pressed="revealed"
            @click="revealed = !revealed"
          >
            <v-icon :icon="revealed ? 'mdi-eye-off' : 'mdi-eye'" />
            <v-tooltip activator="parent" location="bottom">
              {{ revealed ? 'Hide value' : 'Show value' }}
            </v-tooltip>
          </v-btn>
          <!-- A file and a text value exclude each other, so the paperclip is
               off while there is text. It is aria-disabled instead of disabled:
               a disabled button gets no hover or focus, so nobody could learn
               why it is off. -->
          <v-btn
            icon
            variant="text"
            size="small"
            density="comfortable"
            class="secret-row__paperclip"
            aria-label="Upload file as value"
            :aria-disabled="hasValue"
            :aria-describedby="hasValue ? `paperclipHint-${index}` : undefined"
            @click="openFileChooser"
          >
            <v-icon icon="mdi-paperclip" />
            <v-tooltip activator="parent" location="bottom">
              {{ hasValue ? PAPERCLIP_OFF_HINT : 'Upload file as value' }}
            </v-tooltip>
          </v-btn>
          <span v-if="hasValue" :id="`paperclipHint-${index}`" class="d-sr-only">
            {{ PAPERCLIP_OFF_HINT }}
          </span>
        </template>
      </v-textarea>
      <!-- The real file input, which the paperclip opens. It stays in the DOM
           when a file is chosen, so a row keeps one input for its whole life. -->
      <input
        :id="`fileInput-${index}`"
        ref="fileInput"
        type="file"
        class="secret-row__file-input"
        tabindex="-1"
        aria-hidden="true"
        :disabled="hasValue"
        @change="onFileChosen"
      />
    </div>

    <!-- Last in the DOM so that Tab goes key -> value -> actions -> remove; the
         grid puts it where it belongs visually. -->
    <v-btn
      icon
      variant="text"
      size="small"
      class="secret-row__remove"
      :aria-label="`Remove pair ${number}`"
      @click="$emit('remove')"
    >
      <v-icon icon="mdi-trash-can-outline" />
      <v-tooltip activator="parent" location="bottom">Remove pair {{ number }}</v-tooltip>
    </v-btn>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { entryHasFile, entryHasValue, formatFileSize } from '@/utils/secretEntry'
import { rules } from '@/utils/validation'

// Only checked once the field was edited or the form was validated, so a fresh
// row does not start with an error.
const valueRules = [(value) => !!value || 'Must not be empty']
const DUPLICATE_KEY_MESSAGE = 'Duplicate key'
const PAPERCLIP_OFF_HINT = 'Clear the value to upload a file instead'

const props = defineProps({
  entry: {
    type: Object,
    required: true
  },
  // Position in the list, used to give the inputs unique ids.
  index: {
    type: Number,
    required: true
  },
  // True if another row has the same key.
  duplicate: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:key', 'update:value', 'update:file', 'remove'])

const keyField = ref(null)
const fileInput = ref(null)
// Values are masked by default; revealing is a per-row, per-session choice.
const revealed = ref(false)

const number = computed(() => props.index + 1)
const hasValue = computed(() => entryHasValue(props.entry))
const hasFile = computed(() => entryHasFile(props.entry))

function openFileChooser() {
  if (!hasValue.value) fileInput.value.click()
}

function onFileChosen(event) {
  const [file] = event.target.files
  // Forget the selection: the parent decides whether the file is kept, and
  // choosing the same file again after removing it must still fire `change`.
  event.target.value = ''
  if (file) emit('update:file', file)
}

// For flows that add or import rows: to continue typing, or to show right away
// that an imported key is not valid.
defineExpose({
  focusKey: () => keyField.value?.focus(),
  validateKey: () => keyField.value?.validate()
})
</script>

<style scoped>
.secret-row {
  --secret-row-border: var(--line-strong);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) auto;
  grid-template-areas: 'key value remove';
  column-gap: 12px;
  /* Room for the floating label of the next row below an error message. */
  margin-bottom: 8px;
  align-items: start;
}

.secret-row__number {
  display: none;
  grid-area: number;
  font-weight: 600;
}

.secret-row__key {
  grid-area: key;
  min-width: 0;
}

.secret-row__value {
  grid-area: value;
  min-width: 0;
}

.secret-row__remove {
  grid-area: remove;
  /* Centre on the 48px high outlined field. */
  margin-top: 4px;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  transition: color var(--transition-fast);
}

.secret-row__remove:hover,
.secret-row__remove:focus-visible {
  color: rgb(var(--v-theme-error));
}

/* The field's own actions are tools, not content: kept in the background. */
.secret-row__textarea :deep(.v-field__append-inner .v-btn) {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}

/* Looks off, but stays focusable and hoverable so that its hint can be read. */
.secret-row__paperclip[aria-disabled='true'] {
  opacity: var(--v-disabled-opacity);
  cursor: default;
}

.secret-row__file-input {
  display: none;
}

/* Same box as an outlined field, so swapping text area and file keeps the
   row's size. */
.secret-file {
  display: flex;
  align-items: center;
  min-height: 48px;
  padding: 0 8px;
  margin-bottom: 22px;
  border: 1px solid var(--secret-row-border);
  border-radius: var(--radius-md);
  background: var(--inset-bg);
}

.secret-file__chip {
  max-width: 100%;
}

.secret-file__chip :deep(.v-chip__content) {
  min-width: 0;
}

.secret-file__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.secret-file__size {
  flex: none;
}

/* Hides the characters but keeps the real value in the field, so pasting,
   multi-line text and sealing work as usual. */
.secret-value--masked :deep(textarea) {
  -webkit-text-security: disc;
  text-security: disc;
}

@media (max-width: 599.98px) {
  .secret-row {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'number remove'
      'key key'
      'value value';
    row-gap: 8px;
    padding: 8px 12px 0;
    margin-bottom: 12px;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: var(--inset-bg);
  }

  .secret-row__number {
    display: block;
  }

  .secret-row__remove {
    margin-top: 0;
  }
}
</style>
