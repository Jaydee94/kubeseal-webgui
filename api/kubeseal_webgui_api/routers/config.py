from typing import Dict
from os import environ
import logging
import subprocess
import fastapi

MOCK_ENABLED = environ.get("MOCK_ENABLED", False)
LOGGER = logging.getLogger("kubeseal-webgui")

router = fastapi.APIRouter()


@router.get("/config")
def get_configs() -> Dict[str, str]:
    if MOCK_ENABLED:
        return {"kubeseal_version": "0.1.0"}
    try:
        return {
            "kubeseal_version": get_kubeseal_version(),
        }
    except RuntimeError:
        raise fastapi.HTTPException(
            status_code=500, detail="Failed to retrieve application configs."
        )


def get_kubeseal_version() -> str:
    """Retrieve the kubeseal binary version."""
    LOGGER.debug("Retrieving kubeseal binary version.")
    binary = "kubeseal"
    kubeseal_subprocess = subprocess.Popen(
        [binary, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    output, error = kubeseal_subprocess.communicate()
    if error:
        error_message = f"Error in run_kubeseal: {error}"
        LOGGER.error(error_message)
        raise RuntimeError(error_message)

    version = "".join(output.split("\n"))

    return str(version).split(":")[1].replace('"', "").lstrip()
