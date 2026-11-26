"""The clusters a secret can be sealed for.

Every cluster has its own sealed-secrets controller and so its own
certificate: a value sealed with the certificate of one cluster cannot be
unsealed in another. The clusters are configured by an administrator (a JSON
file, see ``KUBESEAL_CLUSTERS_FILE``); a request only names one of them and
never supplies a path.

Without a clusters file there is one cluster called ``default``, sealed with
``KUBESEAL_CERT``: the behaviour before several clusters were supported.
"""

import functools
import hashlib
import json
import re
import ssl
from dataclasses import dataclass
from pathlib import Path

from kubeseal_webgui_api.app_config import settings

DEFAULT_CLUSTER_NAME = "default"

# A lower case DNS label: safe as a file name and as a ConfigMap key, which is
# what the Helm chart derives from it.
CLUSTER_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?$")


class ClusterConfigError(RuntimeError):
    """The clusters file is unusable. Raised at start-up, never per request."""


@dataclass(frozen=True)
class Cluster:
    """One cluster: where its sealing certificate is and what the API can do."""

    name: str
    cert: str
    # The cluster the API runs in. Only for this one the API can list
    # namespaces and read existing SealedSecrets.
    in_cluster: bool = False


def _parse_entry(index: int, entry: object) -> Cluster:
    where = f"entry {index + 1} of the clusters file"
    if not isinstance(entry, dict):
        raise ClusterConfigError(f"{where} is not an object")
    name = entry.get("name")
    if not isinstance(name, str) or not CLUSTER_NAME_PATTERN.match(name):
        raise ClusterConfigError(
            f"{where} needs a 'name' of lower case letters, digits and '-': {name!r}"
        )
    in_cluster = entry.get("inCluster", False)
    if not isinstance(in_cluster, bool):
        raise ClusterConfigError(f"cluster '{name}': 'inCluster' must be true or false")
    cert = entry.get("cert")
    if cert is None and in_cluster:
        # The certificate of the controller of this cluster: the configured one,
        # or the one fetched from the controller at start-up.
        cert = settings.kubeseal_cert
    if not isinstance(cert, str) or not cert:
        raise ClusterConfigError(f"cluster '{name}' needs a 'cert' (a file path)")
    return Cluster(name=name, cert=cert, in_cluster=in_cluster)


def parse_clusters(document: object) -> list[Cluster]:
    """Turn the content of a clusters file into clusters, or say what is wrong."""
    if not isinstance(document, list) or not document:
        raise ClusterConfigError("the clusters file must be a non-empty JSON list")
    clusters = [_parse_entry(index, entry) for index, entry in enumerate(document)]
    names = [cluster.name for cluster in clusters]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ClusterConfigError(f"duplicate cluster names: {', '.join(duplicates)}")
    if sum(cluster.in_cluster for cluster in clusters) > 1:
        raise ClusterConfigError("at most one cluster can have 'inCluster' set")
    return clusters


def load_clusters() -> list[Cluster]:
    """Read the configured clusters. The first one is the default."""
    if not settings.kubeseal_clusters_file:
        return [
            Cluster(
                name=DEFAULT_CLUSTER_NAME,
                cert=settings.kubeseal_cert,
                in_cluster=True,
            )
        ]
    path = Path(settings.kubeseal_clusters_file)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ClusterConfigError(
            f"cannot read clusters file '{path}': {error}"
        ) from None
    return parse_clusters(document)


@functools.cache
def _cached_clusters(clusters_file: str, kubeseal_cert: str) -> tuple[Cluster, ...]:
    # The settings are arguments, so that a changed setting is never answered
    # with clusters read under the old one.
    del clusters_file, kubeseal_cert
    return tuple(load_clusters())


def get_clusters() -> tuple[Cluster, ...]:
    """The clusters, read once per configuration."""
    return _cached_clusters(settings.kubeseal_clusters_file, settings.kubeseal_cert)


def get_cluster(name: str | None) -> Cluster:
    """The named cluster, or the default one without a name.

    Raises ValueError for an unknown name, which the sealing endpoint answers
    with a 400.
    """
    clusters = get_clusters()
    if name is None or name == "":
        return clusters[0]
    for cluster in clusters:
        if cluster.name == name:
            return cluster
    known = ", ".join(cluster.name for cluster in clusters)
    raise ValueError(f"Unknown cluster {name!r}. Known clusters: {known}")


def cert_fingerprint(cert_path: str) -> str | None:
    """SHA-256 fingerprint of a PEM certificate, or None if it cannot be read.

    Lets administrators and users check that a cluster entry holds the
    certificate they think it does: a certificate of the wrong cluster seals
    without an error, and fails only when the secret is deployed.
    """
    try:
        der = ssl.PEM_cert_to_DER_cert(Path(cert_path).read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))
