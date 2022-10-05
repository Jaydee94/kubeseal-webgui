import fastapi
import json

router = fastapi.APIRouter()


@router.get("/config")
def get_configs():
    return json.dumps({"kubeseal_version": "0.1.0"})
