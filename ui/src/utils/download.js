// How long the object URL lives after the click. Some browsers start reading
// the file only after the click handler returned, so it is not revoked at once.
const REVOKE_DELAY_MS = 1000

/**
 * Offers `text` to the user as a file download.
 *
 * @param {string} fileName
 * @param {string} text
 * @param {string} [type] media type of the file
 */
export function downloadTextFile(fileName, text, type = 'application/yaml') {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_DELAY_MS)
}
