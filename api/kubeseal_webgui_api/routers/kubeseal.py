import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from kubeseal_webgui_api.dependencies import get_kubeseal_client
from kubeseal_webgui_api.internal import KubesealClient
from kubeseal_webgui_api.routers.models import Data, KeyValuePair

router = APIRouter()
LOGGER = logging.getLogger("kubeseal-webgui")


@router.post("/secrets", response_model=List[KeyValuePair])
def encrypt(
    data: Data, client: KubesealClient = Depends(get_kubeseal_client)  # noqa: B008
) -> List[KeyValuePair]:
    try:
        result = []

        for secret in data.secrets:
            LOGGER.info(
                "Sealing secret '%s.%s' for namespace '%s' with scope '%s'.",
                data.secret,
                secret.key,
                data.namespace,
                data.scope,
            )
            output = None
            if secret.value is not None:
                output = client.seal_string(
                    secret.decode_value(),
                    data.scope.value,
                    data.secret,
                    data.namespace,
                )
            elif secret.file is not None:
                output = client.seal_bytes(
                    secret.decode_file(),
                    data.scope.value,
                    data.secret,
                    data.namespace,
                )

            if output is not None:
                result.append(KeyValuePair(key=secret.key, value=output))

        return result
    except (KeyError, ValueError) as e:
        raise HTTPException(400, f"Invalid data for sealing secrets: {e}")
    except RuntimeError:
        raise HTTPException(500, "Server is dreaming...")
