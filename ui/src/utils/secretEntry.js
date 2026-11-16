// One row of the key/value list: a key plus either a text value or a file.

let nextEntryId = 1

/**
 * Create an empty row. `id` identifies the row for as long as it exists, so
 * that removing another row does not move validation state between rows.
 * A row takes either a value or a file (see `isFileTooLarge` for the limit
 * the caller has to enforce on files).
 */
export function createSecretEntry({ key = '', value = '', file = null } = {}) {
  return { id: nextEntryId++, key, value, file, fileError: '' }
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

/**
 * The keys that more than one row uses. Empty keys are ignored: a blank row is
 * "not filled in yet", not a duplicate of another blank row.
 */
export function findDuplicateKeys(entries) {
  const seen = new Set()
  const duplicates = new Set()
  for (const { key } of entries) {
    if (key === '') continue
    if (seen.has(key)) duplicates.add(key)
    seen.add(key)
  }
  return duplicates
}

const FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB']

/** A byte count for people: 512 -> "512 B", 1536 -> "1.5 KB". */
export function formatFileSize(bytes) {
  let size = bytes
  let unit = 0
  while (size >= 1024 && unit < FILE_SIZE_UNITS.length - 1) {
    size /= 1024
    unit++
  }
  // Whole bytes need no decimals; "1.0 KB" would look odd next to "512 B".
  const text = unit === 0 ? String(size) : size.toFixed(1).replace(/\.0$/, '')
  return `${text} ${FILE_SIZE_UNITS[unit]}`
}
