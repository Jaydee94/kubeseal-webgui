from pathlib import Path

from pydantic import BaseSettings


class AppSettings(BaseSettings):
    kubeseal_binary: Path = Path("/bin/false")
    kubeseal_cert: Path = Path("/dev/null")
    kubeseal_autofetch: bool = False
    mock_enabled: bool = False
    sealed_secrets_namespace: str = "sealed-secrets"
    sealed_secrets_controller_name: str = "sealed-secrets-controller"
    mock_namespace_count: int = 120

    class Config:
        fields = {
            "sealed_secrets_namespace": {
                "env": ["sealed_secrets_namespace", "KUBESEAL_CONTROLLER_NAMESPACE"],
            },
            "sealed_secrets_controller_name": {
                "env": ["sealed_secrets_controller_name", "KUBESEAL_CONTROLLER_NAME"],
            },
        }


settings = AppSettings()
