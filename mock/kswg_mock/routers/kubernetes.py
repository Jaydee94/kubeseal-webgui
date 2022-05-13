import fastapi

router = fastapi.APIRouter()

@router.get('/namespaces')
def get_namespaces():
    namespace_spec = {}
    namespace_meta = {
      'name': 'mock',
    }
    namespace = {
        'kind': 'Namespace',
        'api_version': 'v1',
        'metadata': namespace_meta,
        'spec': namespace_spec,
    }
    namespaces = [namespace]
    namespace_list = {
        'kind': 'NamespaceList',
        'api_version': 'v1',
        'items': namespaces,
    }

    return namespace_list
