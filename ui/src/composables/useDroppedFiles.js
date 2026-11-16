import { FILE_TOO_LARGE_MESSAGE } from '@/constants'
import { isDotenvFileName, looksLikeDotenv, parseDotenv } from '@/utils/dotenv'
import { createLogger } from '@/utils/logger'
import { createSecretEntry, isEntryBlank } from '@/utils/secretEntry'
import { isFileTooLarge } from '@/utils/validation'

const log = createLogger('drop')

/**
 * Files dropped on the key/value list: a .env file becomes one pair per
 * variable, any other file becomes a pair named after the file.
 *
 * @param {object} options
 * @param {import('vue').Ref<object[]>} options.entries the rows of the list
 * @param {(message: string) => void} options.onSuccess shows what was imported
 * @param {(message: string) => void} options.onError shows what was refused
 * @param {(entries: object[]) => void} [options.onImported] gets the new rows,
 *   once they are in the list
 */
export function useDroppedFiles({ entries, onSuccess, onError, onImported = () => {} }) {
  async function importDroppedFiles(files) {
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
      if (pairs === null) {
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
      // A fresh form starts with one blank row that the import should replace
      // instead of leaving it behind.
      const keep = entries.value.length === 1 && isEntryBlank(entries.value[0]) ? [] : entries.value
      entries.value = [...keep, ...imported]
      onImported(imported)
    }
    if (rejected.length > 0) {
      onError(rejected.join(' '))
    }
    const summary = describeImport(imported.length - fileCount, importedFrom, fileCount)
    if (summary) onSuccess(summary)
  }

  return { importDroppedFiles }
}

// The pairs of a file that is a .env file, `null` if it is not one. A file is
// one by its name, or if it is plain text of nothing but KEY=VALUE lines.
async function readDotenvPairs(file) {
  const named = isDotenvFileName(file.name)
  if (!named && file.type !== 'text/plain') return null
  try {
    const text = await file.text()
    if (named || looksLikeDotenv(text)) return parseDotenv(text)
  } catch (error) {
    log.error(`Failed to read "${file.name}":`, error)
  }
  return null
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
