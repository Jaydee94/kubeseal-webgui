import threading

from kubernetes import config
from kubernetes.client import Configuration

_load_lock = threading.Lock()
_config_loaded = False


def ensure_incluster_config() -> None:
    """Load the in-cluster configuration, once if the client allows it.

    A current kubernetes client keeps the service account token up to date by
    itself after the first load. A client that needs
    `fix_incluster_bearer_token` only refreshes the token under the old key,
    so for such a client the configuration is loaded again on every call.
    """
    global _config_loaded  # noqa: PLW0603 a process-wide "loaded" flag
    with _load_lock:
        if _config_loaded:
            return
        config.load_incluster_config()
        _config_loaded = not fix_incluster_bearer_token()


def fix_incluster_bearer_token() -> bool:
    """Copy the token to the key the client reads; True if that was needed."""
    # kubernetes-client v36 changed auth_settings() to look for 'BearerToken',
    # but incluster_config.py still sets 'authorization' — copy it over.
    cfg = Configuration.get_default_copy()
    if "authorization" in cfg.api_key and "BearerToken" not in cfg.api_key:
        cfg.api_key["BearerToken"] = cfg.api_key["authorization"]
        Configuration.set_default(cfg)
        return True
    return False
