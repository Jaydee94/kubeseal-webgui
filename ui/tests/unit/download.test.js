import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { downloadTextFile } from '@/utils/download'

describe('downloadTextFile', () => {
  let link

  beforeEach(() => {
    vi.useFakeTimers()
    link = { click: vi.fn() }
    vi.stubGlobal('document', {
      createElement: vi.fn(() => link),
      body: { appendChild: vi.fn(), removeChild: vi.fn() }
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:fake')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('downloads the text as a file with the given name', async () => {
    downloadTextFile('db.yaml', 'a: b')

    const blob = URL.createObjectURL.mock.calls[0][0]
    expect(blob.type).toBe('application/yaml')
    expect(await blob.text()).toBe('a: b')
    expect(link.href).toBe('blob:fake')
    expect(link.download).toBe('db.yaml')
    expect(link.click).toHaveBeenCalledOnce()
    expect(document.body.removeChild).toHaveBeenCalledWith(link)
  })

  it('revokes the object URL after the click', () => {
    downloadTextFile('db.yaml', 'a: b')
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()

    vi.runAllTimers()

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:fake')
  })
})
