import { describe, expect, it } from 'vitest'
import { isDotenvFileName, looksLikeDotenv, parseDotenv } from '@/utils/dotenv'

describe('parseDotenv', () => {
  it('reads KEY=VALUE lines in order', () => {
    expect(parseDotenv('A=1\nB=two\nC=')).toEqual([
      { key: 'A', value: '1' },
      { key: 'B', value: 'two' },
      { key: 'C', value: '' }
    ])
  })

  it('ignores blank lines and comments', () => {
    expect(parseDotenv('# heading\n\n  # indented comment\nA=1\n\n')).toEqual([
      { key: 'A', value: '1' }
    ])
  })

  it('accepts an export prefix, spaces around = and Windows line endings', () => {
    expect(parseDotenv('export A=1\r\nexport   B = 2\r\nC =3')).toEqual([
      { key: 'A', value: '1' },
      { key: 'B', value: '2' },
      { key: 'C', value: '3' }
    ])
  })

  it('drops a byte order mark', () => {
    expect(parseDotenv('\uFEFFA=1')).toEqual([{ key: 'A', value: '1' }])
  })

  it('keeps everything after the first = in the value', () => {
    expect(parseDotenv('URL=postgres://u:p@host/db?x=1&y=2')).toEqual([
      { key: 'URL', value: 'postgres://u:p@host/db?x=1&y=2' }
    ])
  })

  it('cuts an unquoted value at a comment but keeps a # inside a word', () => {
    expect(parseDotenv('A=1 # note\nB=a#b\nC=  spaced   ')).toEqual([
      { key: 'A', value: '1' },
      { key: 'B', value: 'a#b' },
      { key: 'C', value: 'spaced' }
    ])
  })

  it('cuts at a comment after a run of whitespace of any kind', () => {
    expect(parseDotenv('A=one \t  # note\nB=two\t#x')).toEqual([
      { key: 'A', value: 'one' },
      { key: 'B', value: 'two' }
    ])
  })

  it('reads a long run of spaces without a comment in linear time', () => {
    // `\s+#` backtracked quadratically here: seconds instead of milliseconds.
    const value = `a${' '.repeat(200_000)}b`
    const start = performance.now()
    expect(parseDotenv(`A=${value}`)).toEqual([{ key: 'A', value }])
    expect(performance.now() - start).toBeLessThan(500)
  })

  it('reads a comment right after the = as an empty value', () => {
    expect(parseDotenv('A= # note\nB=   #note\nC=#hash\nD =# x')).toEqual([
      { key: 'A', value: '' },
      { key: 'B', value: '' },
      { key: 'C', value: '#hash' },
      { key: 'D', value: '# x' }
    ])
  })

  it('reads single-quoted values literally', () => {
    expect(parseDotenv("A='x y # z'\nB='a\\nb'")).toEqual([
      { key: 'A', value: 'x y # z' },
      { key: 'B', value: 'a\\nb' }
    ])
  })

  it('interprets escapes in double-quoted values', () => {
    expect(parseDotenv('A="line1\\nline2"\nB="say \\"hi\\""\nC="a\\\\b"\nD="tab\\there"')).toEqual([
      { key: 'A', value: 'line1\nline2' },
      { key: 'B', value: 'say "hi"' },
      { key: 'C', value: 'a\\b' },
      { key: 'D', value: 'tab\there' }
    ])
  })

  it('keeps unknown escapes as written', () => {
    expect(parseDotenv('A="C:\\dir"')).toEqual([{ key: 'A', value: 'C:\\dir' }])
  })

  it('allows a comment after a quoted value', () => {
    expect(parseDotenv('A="x" # why')).toEqual([{ key: 'A', value: 'x' }])
  })

  it('keeps an empty quoted value', () => {
    expect(parseDotenv('A=""\nB=\'\'')).toEqual([
      { key: 'A', value: '' },
      { key: 'B', value: '' }
    ])
  })

  it('skips malformed lines and keeps the rest', () => {
    const text = [
      'no equals sign',
      '=value without key',
      'MY KEY=has a space in the key',
      'A="never closed',
      'B="closed" trailing',
      'OK=1'
    ].join('\n')
    expect(parseDotenv(text)).toEqual([{ key: 'OK', value: '1' }])
  })

  it('returns a repeated key repeatedly', () => {
    expect(parseDotenv('A=1\nA=2')).toEqual([
      { key: 'A', value: '1' },
      { key: 'A', value: '2' }
    ])
  })

  it('returns nothing for an empty text', () => {
    expect(parseDotenv('')).toEqual([])
  })
})

describe('looksLikeDotenv', () => {
  it('accepts a text of KEY=VALUE lines, comments and blanks', () => {
    expect(looksLikeDotenv('# config\nA=1\n\nexport B="two"\n')).toBe(true)
  })

  it('needs at least one pair', () => {
    expect(looksLikeDotenv('')).toBe(false)
    expect(looksLikeDotenv('# only a comment\n\n')).toBe(false)
  })

  it('rejects a text with any line that is not a pair', () => {
    expect(looksLikeDotenv('A=1\njust some words')).toBe(false)
    expect(looksLikeDotenv('A=1\nB="never closed')).toBe(false)
  })

  it('does not take base64 padding for an assignment', () => {
    expect(looksLikeDotenv('dGVzdA==')).toBe(false)
    expect(looksLikeDotenv('dGVzdA=')).toBe(false)
  })

  it('rejects a PEM block', () => {
    expect(looksLikeDotenv('-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----')).toBe(
      false
    )
  })
})

describe('isDotenvFileName', () => {
  it('matches .env and names ending in .env', () => {
    expect(isDotenvFileName('.env')).toBe(true)
    expect(isDotenvFileName('prod.env')).toBe(true)
    expect(isDotenvFileName('.ENV')).toBe(true)
  })

  it('does not match other names', () => {
    expect(isDotenvFileName('.env.example')).toBe(false)
    expect(isDotenvFileName('environment.txt')).toBe(false)
    expect(isDotenvFileName('env')).toBe(false)
  })
})
