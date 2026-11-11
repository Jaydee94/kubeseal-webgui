import { createLogger } from '@/utils/logger'

const log = createLogger('http')
const REQUEST_ID_HEADER = 'X-Request-ID'

/**
 * Error for a failed HTTP request. `message` is safe to show to the user and
 * carries the HTTP status, the server's error detail and, when available, the
 * request id under which the API and nginx logged the request.
 */
export class HttpError extends Error {
  constructor(message, { status = null, requestId = null, detail = '', cause } = {}) {
    super(message, { cause })
    this.name = 'HttpError'
    this.status = status
    this.requestId = requestId
    this.detail = detail
  }
}

/** Turn the `detail` of a FastAPI error response into one line of text. */
export function describeDetail(detail) {
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    // FastAPI validation errors. Only location and message are used: the
    // "input" field would echo the submitted (possibly secret) value.
    return detail
      .map((item) => `${(item?.loc ?? []).join('.')}: ${item?.msg ?? 'invalid'}`)
      .join('; ')
  }
  return ''
}

async function readErrorDetail(response) {
  let text
  try {
    text = await response.text()
  } catch {
    return ''
  }
  try {
    return describeDetail(JSON.parse(text)?.detail)
  } catch {
    // Not JSON, e.g. an HTML error page from a proxy in front of the API.
    return ''
  }
}

/**
 * fetch() wrapper that logs every request (method, URL, status, duration,
 * request id) and turns network errors and non-2xx responses into HttpError.
 * Request and response bodies are never logged.
 */
export async function request(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const started = performance.now()
  const elapsed = () => `${Math.round(performance.now() - started)}ms`

  let response
  try {
    response = await fetch(url, options)
  } catch (error) {
    log.error(`${method} ${url} failed after ${elapsed()}: no response`, error)
    throw new HttpError(`Could not reach the server (${error.message})`, { cause: error })
  }

  const requestId = response.headers.get(REQUEST_ID_HEADER)
  const idSuffix = requestId ? ` request_id=${requestId}` : ''

  if (!response.ok) {
    const detail = await readErrorDetail(response)
    log.error(`${method} ${url} -> ${response.status} in ${elapsed()}${idSuffix}`, detail)
    const parts = [`HTTP ${response.status}`]
    if (detail) parts.push(detail)
    if (requestId) parts.push(`request id ${requestId}`)
    throw new HttpError(parts.join(' - '), { status: response.status, requestId, detail })
  }

  log.debug(`${method} ${url} -> ${response.status} in ${elapsed()}${idSuffix}`)
  return response
}

export async function requestJson(url, options) {
  const response = await request(url, options)
  try {
    return await response.json()
  } catch (error) {
    log.error(`${(options?.method || 'GET').toUpperCase()} ${url} returned invalid JSON`, error)
    throw new HttpError(`Invalid JSON in response from ${url}`, {
      status: response.status,
      requestId: response.headers.get(REQUEST_ID_HEADER),
      cause: error
    })
  }
}
