import { describe, expect, it } from 'vitest'
import {
  manifestFileName,
  renderSealedSecretYaml,
  scopeAnnotations
} from '@/utils/sealedSecretYaml'

// These are the strings tests/test_ui.py pins for the result view. Users copy
// this text into their repositories, so every character matters, including
// the space after "encryptedData:".
describe('renderSealedSecretYaml', () => {
  it('renders a strict secret', () => {
    const yaml = renderSealedSecretYaml({
      name: 'valid-secret-name',
      namespace: 'my-namespace',
      scope: 'strict',
      entries: [{ key: 'my-secret-key', value: 'AgSealedValue' }]
    })

    expect(yaml).toBe(
      'apiVersion: bitnami.com/v1alpha1\n' +
        'kind: SealedSecret\n' +
        'metadata:\n' +
        '  name: valid-secret-name\n' +
        '  namespace: my-namespace\n' +
        'spec:\n' +
        '  encryptedData: \n' +
        '    my-secret-key: AgSealedValue'
    )
  })

  it('renders a namespace-wide secret without a name', () => {
    const yaml = renderSealedSecretYaml({
      name: '',
      namespace: 'my-namespace',
      scope: 'namespace-wide',
      entries: [{ key: 'my-secret-key', value: 'AgSealedValue' }]
    })

    expect(yaml).toBe(
      'apiVersion: bitnami.com/v1alpha1\n' +
        'kind: SealedSecret\n' +
        'metadata:\n' +
        '  name: # no secret name given\n' +
        '  namespace: my-namespace\n' +
        '  annotations: { sealedsecrets.bitnami.com/namespace-wide: "true" }\n' +
        'spec:\n' +
        '  encryptedData: \n' +
        '    my-secret-key: AgSealedValue'
    )
  })

  it('renders a cluster-wide secret without name and namespace', () => {
    const yaml = renderSealedSecretYaml({
      name: '',
      namespace: '',
      scope: 'cluster-wide',
      entries: [{ key: 'a', value: 'AgA' }]
    })

    expect(yaml).toContain('  name: # no secret name given\n')
    expect(yaml).toContain('  namespace: # no namespace name given\n')
    expect(yaml).toContain('  annotations: { sealedsecrets.bitnami.com/cluster-wide: "true" }\n')
  })

  it('leaves out the annotations of the strict scope only', () => {
    const entries = [{ key: 'a', value: 'AgA' }]
    const render = (scope) => renderSealedSecretYaml({ name: 'n', namespace: 'ns', scope, entries })

    expect(render('strict')).not.toContain('annotations')
    expect(render('namespace-wide')).toContain('  annotations: {')
    expect(render('cluster-wide')).toContain('  annotations: {')
  })

  it('renders one line per key, in the given order', () => {
    const yaml = renderSealedSecretYaml({
      name: 'n',
      namespace: 'ns',
      scope: 'strict',
      entries: [
        { key: 'tls.key', value: 'AgKey' },
        { key: 'tls.crt', value: 'AgCrt' },
        { key: 'API_KEY', value: 'AgApi' }
      ]
    })

    expect(yaml.split('\n').slice(6)).toEqual([
      '  encryptedData: ',
      '    tls.key: AgKey',
      '    tls.crt: AgCrt',
      '    API_KEY: AgApi'
    ])
  })

  it('ends with an empty encryptedData block when there are no entries', () => {
    const yaml = renderSealedSecretYaml({
      name: 'n',
      namespace: 'ns',
      scope: 'strict',
      entries: []
    })
    expect(yaml.endsWith('spec:\n  encryptedData: \n')).toBe(true)
  })
})

describe('scopeAnnotations', () => {
  it.each([
    ['strict', null],
    ['namespace-wide', '{ sealedsecrets.bitnami.com/namespace-wide: "true" }'],
    ['cluster-wide', '{ sealedsecrets.bitnami.com/cluster-wide: "true" }']
  ])('%s -> %s', (scope, annotations) => {
    expect(scopeAnnotations(scope)).toBe(annotations)
  })
})

describe('manifestFileName', () => {
  it('is named after the secret', () => {
    expect(manifestFileName('db-credentials')).toBe('db-credentials.yaml')
  })

  it('falls back to a generic name without a secret name', () => {
    expect(manifestFileName('')).toBe('sealed-secret.yaml')
  })
})
