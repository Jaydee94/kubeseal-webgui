import { defineComponent, h } from 'vue'
import { TOKEN_PLAIN, tokenizeYaml } from '@/utils/yamlHighlight'

/**
 * `<code>` with the YAML text coloured. The text is built from text nodes and
 * spans (never from HTML), so whatever the YAML contains is shown as text and
 * the element's textContent is exactly `text`: selecting and copying it by
 * hand gives the same as the copy button does.
 */
export default defineComponent({
  name: 'YamlCode',
  props: {
    text: {
      type: String,
      required: true
    }
  },
  setup(props) {
    return () => {
      const children = []
      tokenizeYaml(props.text).forEach((line, index) => {
        if (index > 0) children.push('\n')
        for (const token of line) {
          children.push(
            token.type === TOKEN_PLAIN
              ? token.text
              : h('span', { class: `yaml-${token.type}` }, token.text)
          )
        }
      })
      return h('code', children)
    }
  }
})
