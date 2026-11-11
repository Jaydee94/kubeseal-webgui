import { afterEach, describe, expect, it, vi } from 'vitest'
import { HttpError, describeDetail, request, requestJson } from '@/utils/http'
import { setLogLevel } from '@/utils/logger'

setLogLevel('silent')

function jsonResponse(status, body, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers }
  })
}

function stubFetch(implementation) {
  const fetchMock = vi.fn(implementation)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('describeDetail', () => {
  it('returns a string detail unchanged', () => {
    expect(describeDetail('Failed to seal secrets.')).toBe('Failed to seal secrets.')
  })

  it('joins FastAPI validation errors as "location: message"', () => {
    const detail = [
      { loc: ['body', 'secrets', 0], msg: 'Value error, One field has to be set', type: 'x' },
      { loc: ['body', 'scope'], msg: 'Input should be one of ...', type: 'enum' }
    ]
    expect(describeDetail(detail)).toBe(
      'body.secrets.0: Value error, One field has to be set; body.scope: Input should be one of ...'
    )
  })

  it('never includes the submitted input of a validation error', () => {
    const detail = [{ loc: ['body', 'secrets', 0, 'value'], msg: 'bad', input: 'c2VjcmV0' }]
    expect(describeDetail(detail)).not.toContain('c2VjcmV0')
  })

  it('copes with incomplete validation errors', () => {
    expect(describeDetail([{}, null, { loc: ['body'] }])).toBe(
      ': invalid; : invalid; body: invalid'
    )
  })

  it.each([undefined, null, 42, { message: 'x' }])('returns "" for %j', (detail) => {
    expect(describeDetail(detail)).toBe('')
  })
})

describe('HttpError', () => {
  it('carries status, request id and detail', () => {
    const cause = new Error('boom')
    const error = new HttpError('HTTP 500', { status: 500, requestId: 'abc', detail: 'd', cause })
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('HttpError')
    expect(error.message).toBe('HTTP 500')
    expect(error.status).toBe(500)
    expect(error.requestId).toBe('abc')
    expect(error.detail).toBe('d')
    expect(error.cause).toBe(cause)
  })

  it('has empty defaults', () => {
    const error = new HttpError('Could not reach the server')
    expect(error.status).toBeNull()
    expect(error.requestId).toBeNull()
    expect(error.detail).toBe('')
  })
})

describe('request', () => {
  it('returns the response of a successful request', async () => {
    const fetchMock = stubFetch(async () => jsonResponse(200, { ok: true }))
    const response = await request('/config', { method: 'post', body: '{}' })
    expect(response.status).toBe(200)
    expect(fetchMock).toHaveBeenCalledWith('/config', { method: 'post', body: '{}' })
  })

  it('formats status, detail and request id of an error response', async () => {
    stubFetch(async () =>
      jsonResponse(500, { detail: 'Failed to seal secrets.' }, { 'X-Request-ID': 'req-1' })
    )
    const error = await request('/secrets').catch((e) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error.message).toBe('HTTP 500 - Failed to seal secrets. - request id req-1')
    expect(error.status).toBe(500)
    expect(error.requestId).toBe('req-1')
    expect(error.detail).toBe('Failed to seal secrets.')
  })

  it('leaves out what the response does not provide', async () => {
    stubFetch(async () => new Response('<html>Bad Gateway</html>', { status: 502 }))
    const error = await request('/secrets').catch((e) => e)
    expect(error.message).toBe('HTTP 502')
    expect(error.requestId).toBeNull()
    expect(error.detail).toBe('')
  })

  it('reports a network failure without a status', async () => {
    const cause = new TypeError('Failed to fetch')
    stubFetch(async () => {
      throw cause
    })
    const error = await request('/secrets').catch((e) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error.message).toBe('Could not reach the server (Failed to fetch)')
    expect(error.status).toBeNull()
    expect(error.cause).toBe(cause)
  })
})

describe('requestJson', () => {
  it('returns the parsed body', async () => {
    stubFetch(async () => jsonResponse(200, ['default', 'kube-system']))
    await expect(requestJson('/namespaces')).resolves.toEqual(['default', 'kube-system'])
  })

  it('turns a body that is not JSON into an HttpError', async () => {
    stubFetch(
      async () =>
        new Response('<html></html>', { status: 200, headers: { 'X-Request-ID': 'req-2' } })
    )
    const error = await requestJson('/namespaces').catch((e) => e)
    expect(error).toBeInstanceOf(HttpError)
    expect(error.message).toBe('Invalid JSON in response from /namespaces')
    expect(error.status).toBe(200)
    expect(error.requestId).toBe('req-2')
  })
})
