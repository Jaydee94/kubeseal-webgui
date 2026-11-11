import { createLogger } from '@/utils/logger'

const log = createLogger('clipboard')

/**
 * Copying is possible when either the async Clipboard API is present (secure
 * contexts: HTTPS or localhost) or the legacy execCommand fallback can be
 * used. The latter keeps the copy buttons visible when the app is served over
 * plain HTTP, where navigator.clipboard is undefined.
 */
export function isClipboardSupported() {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    return true
  }
  return typeof document !== 'undefined' && typeof document.execCommand === 'function'
}

function copyWithExecCommand(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '-9999px'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  const successful = document.execCommand('copy')
  document.body.removeChild(textarea)
  return successful
}

/** Copy `text` to the clipboard; resolves to whether that worked. */
export async function copyToClipboard(text) {
  // Prefer the asynchronous Clipboard API when available in a secure context.
  if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch (error) {
      log.warn('Clipboard API failed, falling back to execCommand:', error)
    }
  }

  // Fallback for non-secure contexts (e.g. served over plain HTTP).
  try {
    const successful = copyWithExecCommand(text)
    if (!successful) {
      log.warn('Copying to the clipboard via execCommand was rejected.')
    }
    return successful
  } catch (error) {
    log.error('Copying to the clipboard failed:', error)
    return false
  }
}
