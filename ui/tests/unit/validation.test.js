import { describe, expect, it } from 'vitest'
import { isDnsLabel, isDnsSubdomain, isFileTooLarge, rules } from '@/utils/validation'

/** The first message a Vuetify input would show, or `true` if all rules pass. */
function validate(ruleList, value) {
  for (const rule of ruleList) {
    const result = rule(value)
    if (result !== true) return result
  }
  return true
}

describe('isDnsSubdomain', () => {
  it.each(['valid-secret-name', 'my.secret-1', 'a', '1starts-with-digit', 'a'.repeat(253)])(
    'accepts %s',
    (name) => {
      expect(isDnsSubdomain(name)).toBe(true)
    }
  )

  it.each(['Not_Valid', 'a_b', 'a..b', 'a.-b', '-a', 'a-', '.a', 'a.', 'ä', 'a'.repeat(254)])(
    'rejects %s',
    (name) => {
      expect(isDnsSubdomain(name)).toBe(false)
    }
  )

  it.each(['', null, undefined])('returns false (not undefined) for %j', (name) => {
    expect(isDnsSubdomain(name)).toBe(false)
  })
})

describe('isDnsLabel', () => {
  it.each(['not-created-yet', 'default', 'a', '0', 'a'.repeat(63)])('accepts %s', (name) => {
    expect(isDnsLabel(name)).toBe(true)
  })

  it.each(['Not_Valid', 'with.dot', '-a', 'a-', 'with space', '', 'a'.repeat(64)])(
    'rejects %s',
    (name) => {
      expect(isDnsLabel(name)).toBe(false)
    }
  )

  it.each([null, undefined])('rejects %j', (name) => {
    expect(isDnsLabel(name)).toBe(false)
  })
})

describe('rules.validNamespace', () => {
  it('accepts a DNS label', () => {
    expect(validate(rules.validNamespace, 'not-created-yet')).toBe(true)
    expect(validate(rules.validNamespace, 'a'.repeat(63))).toBe(true)
  })

  it.each([
    ['', 'Must not be empty'],
    [null, 'Must not be empty'],
    ['a'.repeat(64), 'Longer than 63 chars'],
    [
      'Not_Valid',
      "Must consist of lower case alphanumerics or '-', and start and end with an alphanumeric"
    ]
  ])('rejects %j with "%s"', (value, message) => {
    expect(validate(rules.validNamespace, value)).toBe(message)
  })
})

describe('rules.validDnsSubdomain (required secret name)', () => {
  it.each(['valid-secret-name', 'my.secret-1', 'a'.repeat(253)])('accepts %s', (value) => {
    expect(validate(rules.validDnsSubdomain, value)).toBe(true)
  })

  it.each([
    ['', 'Must not be empty'],
    [null, 'Must not be empty'],
    ['a'.repeat(254), 'Longer than 253 chars'],
    ['Not_Valid', 'Invalid char. Must be one of lower chars, digits, dashes or dots.'],
    ['-a', 'Must start with a lower char or digit'],
    ['a-', 'Must end with a lower char or digit'],
    ['a..b', 'Not a valid DNS subdomain'],
    ['a.-b', 'Not a valid DNS subdomain']
  ])('rejects %j with "%s"', (value, message) => {
    expect(validate(rules.validDnsSubdomain, value)).toBe(message)
  })
})

describe('rules.optionalDnsSubdomain (secret name outside the strict scope)', () => {
  it.each(['', null, 'valid-secret-name', 'my.secret-1', 'a'.repeat(253)])(
    'accepts %j',
    (value) => {
      expect(validate(rules.optionalDnsSubdomain, value)).toBe(true)
    }
  )

  it('reports the length before the format', () => {
    expect(validate(rules.optionalDnsSubdomain, 'a'.repeat(254))).toBe('Longer than 253 chars')
  })

  it.each(['Not_Valid', 'a_b', 'a..b', 'a.-b'])('rejects %s', (value) => {
    expect(validate(rules.optionalDnsSubdomain, value)).toBe(
      "Must consist of lower case alphanumerics, '-' or '.', and start and end with an alphanumeric"
    )
  })
})

describe('rules.validSecretKey', () => {
  it.each(['my-secret-key', 'tls.crt', 'API_KEY', 'a'])('accepts %s', (value) => {
    expect(validate(rules.validSecretKey, value)).toBe(true)
  })

  it.each([
    ['', 'Must not be empty'],
    ['with space', 'Invalid char. Must be one of lower chars, digits, dash, underscore or dot.'],
    ['a/b', 'Invalid char. Must be one of lower chars, digits, dash, underscore or dot.']
  ])('rejects %j with "%s"', (value, message) => {
    expect(validate(rules.validSecretKey, value)).toBe(message)
  })
})

describe('file size', () => {
  const limit = 1024 * 1024
  const message = 'File size should be less than 1 MB!'

  it('allows exactly 1 MiB and rejects one byte more', () => {
    expect(isFileTooLarge({ size: limit })).toBe(false)
    expect(isFileTooLarge({ size: limit + 1 })).toBe(true)
  })

  it('validates the single file of a single-file input', () => {
    expect(validate(rules.fileSize, { size: 20 })).toBe(true)
    expect(validate(rules.fileSize, { size: limit + 1 })).toBe(message)
  })

  it('validates the file list of a multi-file input', () => {
    expect(validate(rules.fileSize, [{ size: 20 }, { size: limit }])).toBe(true)
    expect(validate(rules.fileSize, [{ size: 20 }, { size: limit + 1 }])).toBe(message)
  })

  it.each([null, undefined])('accepts an empty input (%j)', (value) => {
    expect(validate(rules.fileSize, value)).toBe(true)
  })
})
