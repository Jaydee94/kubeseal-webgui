from typing import List

import fastapi

router = fastapi.APIRouter()


@router.get("/namespaces")

def get_namespaces() -> List[str]:
    return ["foo", "bar"]
