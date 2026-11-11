import { Buffer } from 'node:buffer'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setLogLevel } from '@/utils/logger'

setLogLevel('silent')

const API_URL = 'https://kubeseal.example.com'

describe('api', () => {
  let api
  let requests

  /** Serve config.json and answer every API request with `apiResponse`. */
  function stubFetch(apiResponse) {
    requests = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, options = {}) => {
        if (url === '/config.json') {
          return new Response(JSON.stringify({ api_url: API_URL }))
        }
        requests.push({ url, ...options })
        return new Response(JSON.stringify(apiResponse))
      })
    )
  }

  beforeEach(async () => {
    vi.resetModules()
    api = await import('@/api')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('fetches the namespaces from the configured API', async () => {
    stubFetch(['default', 'kube-system'])
    await expect(api.fetchNamespaces()).resolves.toEqual(['default', 'kube-system'])
    expect(requests).toEqual([{ url: `${API_URL}/namespaces` }])
  })

  it('makes up namespaces only when VITE_MOCK_NAMESPACES is exactly "true"', async () => {
    stubFetch(['from-api'])

    vi.stubEnv('VITE_MOCK_NAMESPACES', 'false')
    await expect(api.fetchNamespaces()).resolves.toEqual(['from-api'])

    vi.stubEnv('VITE_MOCK_NAMESPACES', 'true')
    const mocked = await api.fetchNamespaces()
    expect(mocked).toHaveLength(10)
    expect(mocked).not.toContain('from-api')
    expect(requests).toHaveLength(1)
  })

  it('fetches the SealedSecrets of a namespace', async () => {
    const sealedSecrets = [{ name: 'app-secrets', keys: ['API_KEY'] }]
    stubFetch(sealedSecrets)
    await expect(api.fetchSealedSecrets('team a/b')).resolves.toEqual(sealedSecrets)
    expect(requests).toEqual([{ url: `${API_URL}/sealed-secrets/team%20a%2Fb` }])
  })

  it('fetches the API settings', async () => {
    stubFetch({ kubesealVersion: '0.27.1' })
    await expect(api.fetchApiConfig()).resolves.toEqual({ kubesealVersion: '0.27.1' })
    expect(requests).toEqual([{ url: `${API_URL}/config` }])
  })

  it('posts values and files base64-encoded and returns the sealed values', async () => {
    const sealed = [
      { key: 'password', value: 'AgA' },
      { key: 'keystore', value: 'AgB' }
    ]
    stubFetch(sealed)
    const binary = new Uint8Array([0, 255, 13, 10, 128])

    const result = await api.sealSecrets({
      secretName: 'my-secret',
      namespaceName: 'my-namespace',
      scope: 'strict',
      entries: [
        { id: 1, key: 'password', value: 'pässwörd', file: null, fileError: '' },
        { id: 2, key: 'keystore', value: '', file: new Blob([binary]), fileError: '' }
      ]
    })

    expect(result).toEqual(sealed)
    expect(requests).toHaveLength(1)
    const [request] = requests
    expect(request.url).toBe(`${API_URL}/secrets`)
    expect(request.method).toBe('POST')
    expect(request.headers).toEqual({ 'Content-Type': 'application/json' })
    // only what the API expects is sent: no ids, no error state
    expect(JSON.parse(request.body)).toEqual({
      secret: 'my-secret',
      namespace: 'my-namespace',
      scope: 'strict',
      secrets: [
        { key: 'password', value: Buffer.from('pässwörd', 'utf-8').toString('base64') },
        { key: 'keystore', file: Buffer.from(binary).toString('base64') }
      ]
    })
  })

  it('reads config.json once for several API calls', async () => {
    stubFetch([])
    await api.fetchNamespaces()
    await api.fetchSealedSecrets('default')
    const configRequests = fetch.mock.calls.filter(([url]) => url === '/config.json')
    expect(configRequests).toHaveLength(1)
  })
})
