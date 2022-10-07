import fastapi

router = fastapi.APIRouter()


@router.get("/config")
def get_configs():
    return {"kubeseal_version": "0.1.0"}
