from kubernetes import client, config


class InclusterCoreClient:
    """Proxy implementation for a CoreV1Api object."""

    def __init__(self, api_client=None):
        self.__api_client = api_client

    @staticmethod
    def __str__() -> str:
        return "in-cluster"

    def __getattr__(self, attr: str):
        """Proxy factory to load the API config before calling the target attribute"""

        def wrapped_method(*args, **kwargs):
            config.load_incluster_config()
            core = client.CoreV1Api(api_client=self.__api_client)
            target = getattr(core, attr)
            if callable(target):
                return target(*args, **kwargs)
            return target

        return wrapped_method
