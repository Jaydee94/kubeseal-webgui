import { ref } from 'vue'
import { FILE_TOO_LARGE_MESSAGE } from '@/constants'
import { isDotenvFileName, looksLikeDotenv, parseDotenv } from '@/utils/dotenv'
import { createLogger } from '@/utils/logger'
import { createSecretEntry, isEntryBlank } from '@/utils/secretEntry'
import { isFileTooLarge } from '@/utils/validation'

const log = createLogger('drop')

// Result of readDotenvPairs for a file that could not be read at all.
const UNREADABLE = Symbol('unreadable')

/**
 * Files dropped on the key/value list: a .env file becomes one pair per
 * variable, any other file becomes a pair named after the file.
 *
 * @param {object} options
 * @param {import('vue').Ref<object[]>} options.entries the rows of the list
 * @param {(message: string) => void} options.onSuccess shows what was imported
 * @param {(message: string) => void} options.onError shows what was refused
 * @param {(entries: object[]) => void} [options.onImported] gets the new rows
 *   (only those), once they are in the list
 * @returns {{ importDroppedFiles: (files: File[]) => Promise<void>,
 *   pendingImports: import('vue').Ref<number> }}
 */
export function useDroppedFiles({ entries, onSuccess, onError, onImported = () => {} }) {
  // Drops whose files are still being read. Sealing waits for them, or it
  // would seal the list as it was before the import.
  const pendingImports = ref(0)

  async function importDroppedFiles(files) {
    pendingImports.value++
    try {
      await importFiles(files)
    } finally {
      pendingImports.value--
    }
  }

  async function importFiles(files) {
    const imported = []
    const importedFrom = []
    let fileCount = 0
    const rejected = []

    for (const file of files) {
      if (isFileTooLarge(file)) {
        rejected.push(`${file.name}: ${FILE_TOO_LARGE_MESSAGE}`)
        continue
      }
      const pairs = await readDotenvPairs(file)
      if (pairs === UNREADABLE) {
        // Neither its pairs nor its content could be sealed.
        rejected.push(`${file.name}: Could not read the file.`)
      } else if (pairs === null) {
        imported.push(createSecretEntry({ key: file.name, file }))
        fileCount++
      } else if (pairs.length === 0) {
        rejected.push(`${file.name}: No KEY=VALUE pairs found.`)
      } else {
        imported.push(...pairs.map((pair) => createSecretEntry(pair)))
        importedFrom.push(file.name)
      }
    }

    if (imported.length > 0) {
      // Blank rows (the one of a fresh form, or any "Add pair" that was never
      // filled) are placeholders that the import replaces instead of leaving
      // behind, where they would keep Encrypt disabled.
      const keep = entries.value.filter((entry) => !isEntryBlank(entry))
      entries.value = [...keep, ...imported]
      onImported(imported)
    }
    if (rejected.length > 0) {
      onError(rejected.join(' '))
    }
    const summary = describeImport(imported.length - fileCount, importedFrom, fileCount)
    if (summary) onSuccess(summary)
  }

  return { importDroppedFiles, pendingImports }
}

// The pairs of a file that is a .env file, `null` if it is not one, and
// UNREADABLE if reading it failed. A file is one by its name, or if it is
// plain text of nothing but KEY=VALUE lines.
async function readDotenvPairs(file) {
  const named = isDotenvFileName(file.name)
  if (!named && file.type !== 'text/plain') return null
  let text
  try {
    text = await file.text()
  } catch (error) {
    log.error(`Failed to read "${file.name}":`, error)
    return UNREADABLE
  }
  return named || looksLikeDotenv(text) ? parseDotenv(text) : null
}

function describeImport(keyCount, sources, fileCount) {
  const parts = []
  if (keyCount > 0) {
    parts.push(`Imported ${keyCount} ${keyCount === 1 ? 'key' : 'keys'} from ${sources.join(', ')}`)
  }
  if (fileCount > 0) {
    parts.push(
      `${parts.length > 0 ? 'added' : 'Added'} ${fileCount} ${fileCount === 1 ? 'file' : 'files'}`
    )
  }
  return parts.join(' and ')
}
