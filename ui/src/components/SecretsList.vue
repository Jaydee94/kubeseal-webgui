<template>
  <!-- The whole section is the drop target, so that a file can be dropped
       wherever the pairs are, not only on one small spot. -->
  <div
    class="secrets-list"
    @dragenter="onDragEnter"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <div v-if="dragging" class="drop-zone" aria-hidden="true">
      <div class="drop-zone__label">
        <v-icon icon="mdi-file-upload-outline" size="large" class="mr-2" />
        Drop .env or files here
      </div>
    </div>

    <v-divider class="my-6" />

    <!-- Wraps, so that every action stays reachable on a narrow screen. -->
    <div class="d-flex flex-wrap justify-space-between align-center ga-2 mb-3">
      <div class="d-flex align-center">
        <v-card-subtitle class="text-subtitle-2 px-0 mr-2">Secret Key-Value Pairs</v-card-subtitle>
        <InfoTooltip>
          <span
            >Specify sensitive value and corresponding key of the secret.<br /><i
              >The key must be of type: DNS Subdomain</i
            ></span
          >
        </InfoTooltip>
      </div>
      <div class="d-flex flex-wrap align-center">
        <slot name="header-actions" />
        <v-btn
          prepend-icon="mdi-delete-sweep"
          variant="text"
          color="error"
          size="small"
          class="text-caption"
          @click="$emit('remove-all')"
        >
          Remove All
        </v-btn>
      </div>
    </div>

    <SecretInput
      v-for="(entry, index) in entries"
      :key="entry.id"
      :ref="(row) => setRow(entry.id, row)"
      :entry="entry"
      :index="index"
      :duplicate="duplicateKeys.has(entry.key)"
      @update:key="$emit('update-entry', entry.id, { key: $event })"
      @update:value="$emit('update-entry', entry.id, { value: $event })"
      @update:file="$emit('select-file', entry.id, $event)"
      @remove="$emit('remove-entry', entry.id)"
    />

    <v-row>
      <v-col>
        <v-btn
          block
          variant="outlined"
          style="border-style: dashed; border-width: 2px; opacity: 0.8"
          prepend-icon="mdi-plus"
          color="primary"
          class="mb-4"
          @click="$emit('add-entry')"
        >
          Add key-value pair
        </v-btn>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { carriesFiles } from '@/utils/dragDrop'
import InfoTooltip from './InfoTooltip.vue'
import SecretInput from './SecretInput.vue'

defineProps({
  entries: {
    type: Array,
    required: true
  },
  // Keys that more than one row uses.
  duplicateKeys: {
    type: Set,
    default: () => new Set()
  }
})

// The rows by entry id, so that the parent can move focus into a row.
const rows = new Map()
function setRow(id, row) {
  if (row) rows.set(id, row)
  else rows.delete(id)
}

defineExpose({
  focusKey: (id) => rows.get(id)?.focusKey(),
  validateKey: (id) => rows.get(id)?.validateKey()
})

const emit = defineEmits([
  'update-entry',
  'select-file',
  'add-entry',
  'remove-entry',
  'remove-all',
  'drop-files'
])

// Dragging a file over the section. `dragenter`/`dragleave` also fire for every
// child the pointer crosses, so the zone is only left when they balance out.
const dragging = ref(false)
let dragDepth = 0

function onDragEnter(event) {
  if (!carriesFiles(event)) return
  event.preventDefault()
  dragDepth++
  dragging.value = true
}

function onDragOver(event) {
  if (!carriesFiles(event)) return
  // Without this the browser refuses the drop and opens the file instead.
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
}

function onDragLeave(event) {
  if (!carriesFiles(event)) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragging.value = false
}

function onDrop(event) {
  if (!carriesFiles(event)) return
  event.preventDefault()
  dragDepth = 0
  dragging.value = false
  const files = droppedFiles(event.dataTransfer)
  if (files.length > 0) emit('drop-files', files)
}

// Folders arrive as pseudo-files that cannot be read, so they are left out.
// The entries have to be looked at while the event is handled.
function droppedFiles(dataTransfer) {
  const items = Array.from(dataTransfer.items ?? []).filter((item) => item.kind === 'file')
  if (items.length === 0) return Array.from(dataTransfer.files)
  return items
    .filter((item) => !item.webkitGetAsEntry?.()?.isDirectory)
    .map((item) => item.getAsFile())
    .filter(Boolean)
}
</script>

<style scoped>
.secrets-list {
  position: relative;
}

/* Covers the section without catching the pointer, so the drag events keep
   going to the rows below. */
.drop-zone {
  position: absolute;
  /* A little wider than the rows, so the border does not touch their fields. */
  inset: 0 -8px;
  z-index: 2;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 24px 16px;
  border: 2px dashed rgb(var(--v-theme-primary));
  border-radius: 12px;
  background: rgba(var(--v-theme-primary), 0.08);
  pointer-events: none;
  animation: drop-zone-in 120ms ease-out;
}

/* Stays in view while a long list is scrolled past. */
.drop-zone__label {
  position: sticky;
  top: 35vh;
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

@keyframes drop-zone-in {
  from {
    opacity: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .drop-zone {
    animation: none;
  }
}
</style>
