// One row of the key/value list: a key plus either a text value or a file.

let nextEntryId = 1

/**
 * Create an empty row. `id` identifies the row for as long as it exists, so
 * that removing another row does not move validation state between rows.
 */
export function createSecretEntry({ key = '' } = {}) {
  return { id: nextEntryId++, key, value: '', file: null, fileError: '' }
}

export function entryHasValue(entry) {
  return entry.value !== ''
}

export function entryHasFile(entry) {
  return entry.file instanceof Blob
}

/** True while the row has neither a key nor anything to seal. */
export function isEntryBlank(entry) {
  return entry.key === '' && !entryHasValue(entry) && !entryHasFile(entry)
}

/** True if the row can be sealed: a key and a value or a file. */
export function isEntryComplete(entry) {
  return entry.key !== '' && (entryHasValue(entry) || entryHasFile(entry))
}
