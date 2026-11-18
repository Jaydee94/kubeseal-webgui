// A small YAML tokenizer for colouring the generated manifest. It is meant for
// what this app renders (block mappings, one flow mapping, comments), not for
// all of YAML: whatever it does not understand is returned as plain text.
//
// The tokens only carry text. How they are shown is up to the caller, which
// has to escape them (the Vue component does so by construction). The text of
// all tokens put together is always exactly the input, so highlighting never
// changes what is copied.

export const TOKEN_PLAIN = 'plain'
export const TOKEN_KEY = 'key'
export const TOKEN_PUNCTUATION = 'punctuation'
export const TOKEN_STRING = 'string'
export const TOKEN_VALUE = 'value'
export const TOKEN_COMMENT = 'comment'

const FLOW_OPENERS = '{['
const FLOW_CLOSERS = '}]'

function isWhitespace(char) {
  return char === ' ' || char === '\t'
}

// "key:" is a key only when the colon ends the text or is followed by a space.
function isKeyColon(line, index) {
  return line[index] === ':' && (index + 1 >= line.length || isWhitespace(line[index + 1]))
}

// A comment starts at a "#" at the start of a line or after whitespace.
function startsComment(line, index) {
  return line[index] === '#' && (index === 0 || isWhitespace(line[index - 1]))
}

// The end (exclusive) of a quoted scalar that starts at `start`. A quote that
// is never closed runs to the end of the line.
function quotedEnd(line, start) {
  const quote = line[start]
  let index = start + 1
  while (index < line.length) {
    if (quote === '"' && line[index] === '\\') {
      index += 2
      continue
    }
    if (line[index] === quote) {
      return index + 1
    }
    index++
  }
  return line.length
}

// The end (exclusive) of a plain scalar that starts at `start`.
function plainEnd(line, start, depth, canBeKey) {
  let index = start
  while (index < line.length) {
    if (startsComment(line, index)) break
    if (canBeKey && isKeyColon(line, index)) break
    if (depth > 0 && (line[index] === ',' || FLOW_CLOSERS.includes(line[index]))) break
    index++
  }
  // Whitespace before a comment or a delimiter is not part of the scalar.
  while (index > start && isWhitespace(line[index - 1])) index--
  return index
}

function tokenizeLine(line) {
  const tokens = []
  const push = (type, text) => {
    if (text === '') return
    const last = tokens[tokens.length - 1]
    if (last && last.type === type && type === TOKEN_PLAIN) {
      last.text += text
    } else {
      tokens.push({ type, text })
    }
  }

  let index = 0
  let depth = 0
  // Where a key may start: the start of the line, a list item, or inside a
  // flow collection after its opening bracket or a comma.
  let canBeKey = true

  while (index < line.length) {
    const char = line[index]

    if (isWhitespace(char)) {
      push(TOKEN_PLAIN, char)
      index++
    } else if (startsComment(line, index)) {
      push(TOKEN_COMMENT, line.slice(index))
      index = line.length
    } else if (depth === 0 && canBeKey && char === '-' && isKeyColonOrSpace(line, index + 1)) {
      push(TOKEN_PUNCTUATION, '-')
      index++
    } else if (FLOW_OPENERS.includes(char)) {
      push(TOKEN_PUNCTUATION, char)
      depth++
      canBeKey = true
      index++
    } else if (depth > 0 && FLOW_CLOSERS.includes(char)) {
      push(TOKEN_PUNCTUATION, char)
      depth--
      canBeKey = false
      index++
    } else if (depth > 0 && char === ',') {
      push(TOKEN_PUNCTUATION, char)
      canBeKey = true
      index++
    } else if (canBeKey && isKeyColon(line, index)) {
      // An empty key, as in ": value".
      push(TOKEN_PUNCTUATION, ':')
      canBeKey = false
      index++
    } else {
      const quoted = char === '"' || char === "'"
      const end = quoted ? quotedEnd(line, index) : plainEnd(line, index, depth, canBeKey)
      const text = line.slice(index, end)
      // Guards against a scalar that makes no progress (e.g. a lone ",").
      if (end === index) {
        push(TOKEN_PLAIN, char)
        index++
        continue
      }
      if (canBeKey && isKeyColon(line, end)) {
        push(TOKEN_KEY, text)
        push(TOKEN_PUNCTUATION, ':')
        index = end + 1
      } else {
        push(quoted ? TOKEN_STRING : TOKEN_VALUE, text)
        index = end
      }
      canBeKey = false
    }
  }
  return tokens
}

function isKeyColonOrSpace(line, index) {
  return index >= line.length || isWhitespace(line[index])
}

/**
 * @param {string} text YAML text
 * @returns {{type: string, text: string}[][]} the tokens of every line; a
 *   line's tokens joined give the line, and the lines joined by "\n" the text
 */
export function tokenizeYaml(text) {
  return text.split('\n').map(tokenizeLine)
}
