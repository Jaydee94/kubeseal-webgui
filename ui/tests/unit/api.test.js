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
        if (url === 'config.json') {
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

  it('fetches the clusters to seal for', async () => {
    const clusters = [
      { name: 'acc', inCluster: true, fingerprint: 'AA:BB' },
      { name: 'prod', inCluster: false, fingerprint: null }
    ]
    stubFetch(clusters)
    await expect(api.fetchClusters()).resolves.toEqual(clusters)
    expect(requests).toEqual([{ url: `${API_URL}/clusters` }])
  })

  it('has no clusters when the API is missing in mock mode, and fails otherwise', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => {
        if (url === 'config.json') {
          return new Response(JSON.stringify({ api_url: API_URL }))
        }
        return new Response('no API', { status: 500 })
      })
    )

    vi.stubEnv('VITE_MOCK_NAMESPACES', 'true')
    await expect(api.fetchClusters()).resolves.toEqual([])

    vi.stubEnv('VITE_MOCK_NAMESPACES', 'false')
    await expect(api.fetchClusters()).rejects.toThrow()
  })

  it('reads only a missing endpoint as an API without clusters', () => {
    expect(api.clustersNotSupported({ status: 404 })).toBe(true)
    expect(api.clustersNotSupported({ status: 500 })).toBe(false)
    expect(api.clustersNotSupported({ status: 502 })).toBe(false)
    // a network error or an unreadable answer has no status
    expect(api.clustersNotSupported(new Error('Invalid JSON'))).toBe(false)
    expect(api.clustersNotSupported(undefined)).toBe(false)
  })

  it('names the cluster in the sealing request, and leaves it out without one', async () => {
    stubFetch([])
    const entries = [{ id: 1, key: 'k', value: 'v', file: null, fileError: '' }]
    const seal = (cluster) =>
      api.sealSecrets({
        secretName: 'name',
        namespaceName: 'ns',
        scope: 'strict',
        entries,
        cluster
      })

    await seal('prod')
    await seal('')
    await seal(undefined)

    const bodies = requests.map((request) => JSON.parse(request.body))
    expect(bodies[0].cluster).toBe('prod')
    expect(bodies[1]).not.toHaveProperty('cluster')
    expect(bodies[2]).not.toHaveProperty('cluster')
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

  it('sends a row without a file as a value, even an empty one', async () => {
    stubFetch([{ key: 'empty', value: 'AgA' }])

    await api.sealSecrets({
      secretName: 'my-secret',
      namespaceName: 'my-namespace',
      scope: 'strict',
      entries: [{ id: 1, key: 'empty', value: '', file: null, fileError: '' }]
    })

    expect(JSON.parse(requests[0].body).secrets).toEqual([{ key: 'empty', value: '' }])
  })

  it('calls the API next to the page when no API URL is configured', async () => {
    requests = []
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, options = {}) => {
        if (url === 'config.json') {
          return new Response(JSON.stringify({ api_url: '' }))
        }
        requests.push({ url, ...options })
        return new Response('[]')
      })
    )
    await api.fetchNamespaces()
    // relative, so that it also works under a path prefix
    expect(requests).toEqual([{ url: 'namespaces' }])
  })

  it('joins the API URL and an endpoint with exactly one slash', () => {
    expect(api.joinApiUrl('', 'secrets')).toBe('secrets')
    expect(api.joinApiUrl(undefined, 'secrets')).toBe('secrets')
    expect(api.joinApiUrl('https://example.com', 'secrets')).toBe('https://example.com/secrets')
    expect(api.joinApiUrl('https://example.com/kubeseal-webgui/', 'secrets')).toBe(
      'https://example.com/kubeseal-webgui/secrets'
    )
    expect(api.joinApiUrl('/kubeseal-webgui', 'config')).toBe('/kubeseal-webgui/config')
  })

  it('reads config.json once for several API calls', async () => {
    stubFetch([])
    await api.fetchNamespaces()
    await api.fetchSealedSecrets('default')
    const configRequests = fetch.mock.calls.filter(([url]) => url === 'config.json')
    expect(configRequests).toHaveLength(1)
  })
})
