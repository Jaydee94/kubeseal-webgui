from kubernetes.client import Configuration


def fix_incluster_bearer_token() -> None:
    # kubernetes-client v36 changed auth_settings() to look for 'BearerToken',
    # but incluster_config.py still sets 'authorization' — copy it over.
    cfg = Configuration.get_default_copy()
    if "authorization" in cfg.api_key and "BearerToken" not in cfg.api_key:
        cfg.api_key["BearerToken"] = cfg.api_key["authorization"]
        Configuration.set_default(cfg)
