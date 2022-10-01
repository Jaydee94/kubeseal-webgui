import fastapi
import json

router = fastapi.APIRouter()


@router.get("/namespaces")
def get_namespaces():
    return json.dumps(["foo", "bar"])
