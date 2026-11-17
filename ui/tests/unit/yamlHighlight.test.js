import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import YamlCode from '@/components/YamlCode'
import { renderSealedSecretYaml } from '@/utils/sealedSecretYaml'
import { tokenizeYaml } from '@/utils/yamlHighlight'

const line = (text) => tokenizeYaml(text)[0].map(({ type, text: part }) => [type, part])

describe('tokenizeYaml', () => {
  it('splits a mapping line into indent, key, colon and value', () => {
    expect(line('  name: my-secret')).toEqual([
      ['plain', '  '],
      ['key', 'name'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['value', 'my-secret']
    ])
  })

  it('keeps a key whose value is on the following lines', () => {
    expect(line('metadata:')).toEqual([
      ['key', 'metadata'],
      ['punctuation', ':']
    ])
    expect(line('  encryptedData: ')).toEqual([
      ['plain', '  '],
      ['key', 'encryptedData'],
      ['punctuation', ':'],
      ['plain', ' ']
    ])
  })

  it('colours a comment after a key', () => {
    expect(line('  name: # no secret name given')).toEqual([
      ['plain', '  '],
      ['key', 'name'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['comment', '# no secret name given']
    ])
  })

  it('colours a whole-line comment and an end-of-line comment', () => {
    expect(line('# hello')).toEqual([['comment', '# hello']])
    expect(line('a: b # note')).toEqual([
      ['key', 'a'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['value', 'b'],
      ['plain', ' '],
      ['comment', '# note']
    ])
  })

  it('does not take a "#" inside a value for a comment', () => {
    expect(line('a: b#c')).toContainEqual(['value', 'b#c'])
  })

  it('does not take a colon inside a value for a key', () => {
    expect(line('url: http://example.com:8080/x')).toEqual([
      ['key', 'url'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['value', 'http://example.com:8080/x']
    ])
  })

  it('colours quoted strings, with escaped quotes', () => {
    expect(line('a: "x \\" y"')).toContainEqual(['string', '"x \\" y"'])
    expect(line("a: 'it'")).toContainEqual(['string', "'it'"])
  })

  it('tokenizes a flow mapping', () => {
    expect(line('  annotations: { sealedsecrets.bitnami.com/cluster-wide: "true" }')).toEqual([
      ['plain', '  '],
      ['key', 'annotations'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['punctuation', '{'],
      ['plain', ' '],
      ['key', 'sealedsecrets.bitnami.com/cluster-wide'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['string', '"true"'],
      ['plain', ' '],
      ['punctuation', '}']
    ])
    expect(line('a: {}')).toEqual([
      ['key', 'a'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['punctuation', '{'],
      ['punctuation', '}']
    ])
  })

  it('does not take commas of a plain value for flow punctuation', () => {
    expect(line('a: b, c')).toContainEqual(['value', 'b, c'])
  })

  it('marks the dash of a list item', () => {
    expect(line('  - name: x')).toEqual([
      ['plain', '  '],
      ['punctuation', '-'],
      ['plain', ' '],
      ['key', 'name'],
      ['punctuation', ':'],
      ['plain', ' '],
      ['value', 'x']
    ])
  })

  it('returns blank lines and odd input as plain text', () => {
    expect(tokenizeYaml('')).toEqual([[]])
    expect(line('   ')).toEqual([['plain', '   ']])
    expect(tokenizeYaml('a\n\nb')).toHaveLength(3)
  })

  it.each([
    '',
    'just text',
    ': : :',
    'a: "unterminated',
    "a: 'unterminated",
    'a: { b, c: [1, 2], }',
    '}}],,{{',
    '- - - x',
    '\tkey:\tvalue\t# c\t',
    'a: \\',
    '    my-key: AgBase64+/==',
    'x: #',
    '# only'
  ])('loses and adds no character for %j', (text) => {
    const rebuilt = tokenizeYaml(text)
      .map((tokens) => tokens.map((token) => token.text).join(''))
      .join('\n')
    expect(rebuilt).toBe(text)
  })

  it('reproduces a rendered manifest exactly', () => {
    for (const scope of ['strict', 'namespace-wide', 'cluster-wide']) {
      const manifest = renderSealedSecretYaml({
        name: scope === 'strict' ? 'db' : '',
        namespace: scope === 'cluster-wide' ? '' : 'ns',
        scope,
        entries: [
          { key: 'tls.key', value: 'AgA+/=' },
          { key: 'API_KEY', value: 'AgB' }
        ]
      })
      const rebuilt = tokenizeYaml(manifest)
        .map((tokens) => tokens.map((token) => token.text).join(''))
        .join('\n')
      expect(rebuilt).toBe(manifest)
    }
  })
})

async function renderYaml(text) {
  return renderToString(createSSRApp({ render: () => h(YamlCode, { text, id: 'result' }) }))
}

describe('YamlCode', () => {
  it('shows markup in the YAML as text, never as elements', async () => {
    const payload = 'a: <script>alert("x")</script> & "<b>q</b>" # <img src=x onerror=y>'
    const html = await renderYaml(payload)

    expect(html).not.toContain('<script')
    expect(html).not.toContain('<b>')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;script&gt;')
    expect(html).toContain('&amp;')
  })

  it('keeps the text of the element identical to the YAML', async () => {
    const manifest = renderSealedSecretYaml({
      name: 'db',
      namespace: 'ns',
      scope: 'strict',
      entries: [{ key: 'k', value: 'AgA' }]
    })
    const html = await renderYaml(manifest)

    // The markup consists of the code element and its token spans only, so
    // splitting at those tags leaves exactly the escaped text.
    const tags = html.match(/<[^>]+>/g)
    expect(tags.every((tag) => /^<\/?(code|span)[\s>]/.test(tag))).toBe(true)
    const text = html
      .split(/<\/?(?:code|span)[^>]*>/)
      .join('')
      .replaceAll('&quot;', '"')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&amp;', '&')
    expect(text).toBe(manifest)
    expect(html).toContain('<span class="yaml-key">metadata</span>')
    expect(html).toContain('id="result"')
  })
})
