import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { normalizeConfig, toBoolean } from '@/config'
import { setLogLevel } from '@/utils/logger'

setLogLevel('silent')

const CHART_CONFIG = {
  api_url: 'https://kubeseal.example.com',
  display_name: 'Production',
  enable_existing_sealed_secret_loading: true,
  kubeseal_webgui_ui_version: '4.14.0',
  kubeseal_webgui_api_version: '4.14.1'
}

describe('toBoolean', () => {
  it.each([true, 'true', 'True', 'TRUE', '1', 'yes', 'on'])('%j is true', (value) => {
    expect(toBoolean(value)).toBe(true)
  })

  it.each([false, 'false', '0', 'no', 'off', '', 'enabled', 1, null, undefined])(
    '%j is false',
    (value) => {
      expect(toBoolean(value)).toBe(false)
    }
  )
})

describe('normalizeConfig', () => {
  it('translates the keys of config.json', () => {
    expect(normalizeConfig(CHART_CONFIG)).toEqual({
      apiUrl: 'https://kubeseal.example.com',
      displayName: 'Production',
      importEnabled: true,
      uiVersion: '4.14.0',
      apiVersion: '4.14.1'
    })
  })

  it('accepts the feature flag as a string', () => {
    const config = { ...CHART_CONFIG, enable_existing_sealed_secret_loading: 'false' }
    expect(normalizeConfig(config).importEnabled).toBe(false)
  })

  it.each([{}, null, undefined])('has safe defaults for %j', (raw) => {
    expect(normalizeConfig(raw)).toEqual({
      apiUrl: '',
      displayName: '',
      importEnabled: false,
      uiVersion: undefined,
      apiVersion: undefined
    })
  })
})

describe('loadConfig', () => {
  let loadConfig

  beforeEach(async () => {
    // a fresh module, so that no test sees the cached config of another
    vi.resetModules()
    ;({ loadConfig } = await import('@/config'))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function stubFetch(implementation) {
    const fetchMock = vi.fn(implementation)
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  it('requests config.json once for any number of callers', async () => {
    const fetchMock = stubFetch(async () => new Response(JSON.stringify(CHART_CONFIG)))

    const [first, second] = await Promise.all([loadConfig(), loadConfig()])
    const third = await loadConfig()

    expect(fetchMock).toHaveBeenCalledExactlyOnceWith('/config.json', {})
    expect(first.apiUrl).toBe('https://kubeseal.example.com')
    expect(second).toBe(first)
    expect(third).toBe(first)
  })

  it('tries again after a failed request', async () => {
    const fetchMock = stubFetch(async () => new Response('Bad Gateway', { status: 502 }))
    await expect(loadConfig()).rejects.toThrow('HTTP 502')
    await expect(loadConfig()).rejects.toThrow('HTTP 502')
    expect(fetchMock).toHaveBeenCalledTimes(2)

    fetchMock.mockImplementation(async () => new Response(JSON.stringify(CHART_CONFIG)))
    await expect(loadConfig()).resolves.toMatchObject({ displayName: 'Production' })
    await loadConfig()
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
