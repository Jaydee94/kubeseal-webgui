import fastapi

from kubeseal_webgui_api.clusters import cert_fingerprint, get_clusters
from kubeseal_webgui_api.routers.models import ClusterInfo

router = fastapi.APIRouter()


@router.get("/clusters", response_model=list[ClusterInfo])
def list_clusters() -> list[ClusterInfo]:
    """The clusters a secret can be sealed for. The first one is the default."""
    return [
        ClusterInfo(
            name=cluster.name,
            in_cluster=cluster.in_cluster,
            fingerprint=cert_fingerprint(cluster.cert),
        )
        for cluster in get_clusters()
    ]
