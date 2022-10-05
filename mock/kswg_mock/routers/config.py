from typing import Dict

import fastapi

router = fastapi.APIRouter()


@router.get("/config")
def get_configs() -> Dict[str, str]:
    return {"kubeseal_version": "0.1.0"}
