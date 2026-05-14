from typing import List

from kubeseal_webgui_api.routers.models import ExistingSealedSecret


def mock_sealed_secret_resolver(namespace: str) -> List[ExistingSealedSecret]:
    return [
        ExistingSealedSecret(
            name=f"{namespace}-app-secrets",
            keys=["API_KEY", "API_SECRET", "TOKEN"],
        ),
        ExistingSealedSecret(
            name=f"{namespace}-db-secrets",
            keys=["DATABASE", "HOST", "PASSWORD", "PORT", "USERNAME"],
        ),
    ]
