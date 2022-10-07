import fastapi

router = fastapi.APIRouter()


@router.get("/namespaces")
def get_namespaces():
    return ["foo", "bar"]
