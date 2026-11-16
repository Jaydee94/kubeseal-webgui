// A small .env reader, so that a dropped file can fill the key/value list.
// It covers what is common in practice -- KEY=VALUE, `export KEY=VALUE`,
// comments and quoting -- not the full dotenv dialect (no variable expansion,
// no values that span lines).

// The same characters a secret key may have (see `rules.validSecretKey`), so
// that an imported key is not rejected by the form right away.
const KEY = '[A-Za-z0-9_.-]+'
// What follows '=' is kept as written: whether a '#' is preceded by whitespace
// tells a comment (`A= # note`) from data (`A=#hash`).
const ASSIGNMENT = new RegExp(`^(?:export\\s+)?(${KEY})\\s*=(.*)$`)

const ESCAPES = { n: '\n', r: '\r', t: '\t', '"': '"', '\\': '\\' }

/**
 * Reads the value that starts `text` (the part after '='). Returns the value
 * or `null` if the line is malformed, e.g. a quote that is never closed or
 * text after the closing quote.
 */
function readValue(raw) {
  const text = raw.trimStart()
  const quote = text[0]
  if (quote !== '"' && quote !== "'") {
    // An unquoted value ends at a ` #` comment, which can be the whole value;
    // a '#' inside a word is data.
    if (text.length < raw.length && text.startsWith('#')) return ''
    return text.replace(/\s+#.*$/, '').trim()
  }

  let value = ''
  for (let i = 1; i < text.length; i++) {
    const char = text[i]
    if (char === quote) {
      return isEndOfValue(text.slice(i + 1)) ? value : null
    }
    // Only double quotes interpret escapes; single quotes are literal.
    if (quote === '"' && char === '\\' && i + 1 < text.length) {
      const next = text[++i]
      value += ESCAPES[next] ?? `\\${next}`
    } else {
      value += char
    }
  }
  return null
}

function isEndOfValue(rest) {
  const trimmed = rest.trim()
  return trimmed === '' || trimmed.startsWith('#')
}

/** One line as `{ key, value }`, or `null` for blanks, comments and malformed lines. */
function parseLine(line) {
  const trimmed = line.trim()
  if (trimmed === '' || trimmed.startsWith('#')) return null
  const match = ASSIGNMENT.exec(trimmed)
  if (!match) return null
  const value = readValue(match[2])
  return value === null ? null : { key: match[1], value }
}

function lines(text) {
  // A byte order mark would otherwise end up in the first key.
  return text.replace(/^\uFEFF/, '').split(/\r?\n/)
}

/**
 * The `{ key, value }` pairs of a .env text, in order. Malformed lines are
 * skipped. A key that appears twice is returned twice, so that the caller can
 * show the conflict instead of silently picking one.
 */
export function parseDotenv(text) {
  return lines(text).map(parseLine).filter(Boolean)
}

/**
 * Whether a text that is not named `.env` is nevertheless one: every line that
 * is not blank or a comment is a `KEY=VALUE` pair, and there is at least one.
 * Stricter than `parseDotenv`, because here a wrong guess turns a plain file
 * into keys. A line like `dGVzdA==` (base64 padding) must stay a plain value,
 * so empty values and values starting with '=' do not count.
 */
export function looksLikeDotenv(text) {
  const candidates = lines(text)
    .map((line) => line.trim())
    .filter((line) => line !== '' && !line.startsWith('#'))
  if (candidates.length === 0) return false
  return candidates.every((line) => {
    const pair = parseLine(line)
    return pair !== null && pair.value !== '' && !pair.value.startsWith('=')
  })
}

/** True for `.env` and `*.env` (`prod.env`), but not for `.env.example`. */
export function isDotenvFileName(name) {
  const lower = name.toLowerCase()
  return lower === '.env' || lower.endsWith('.env')
}
