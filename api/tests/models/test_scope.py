import pytest

from kubeseal_webgui_api.routers.models import Secret


@pytest.mark.parametrize(
    ("value", "expected_output"),
    [
        (Scope.STRICT, False),
        (Scope.CLUSTER_WIDE, True),
        (Scope.NAMESPACE_WIDE, True),
    ],
)
def test_needs_name(subject, expected_output):
    assert subject.needs_name == expected_output


@pytest.mark.parametrize(
    ("value", "expected_output"),
    [
        (Scope.STRICT, False),
        (Scope.CLUSTER_WIDE, True),
        (Scope.NAMESPACE_WIDE, False),
    ],
)
def test_needs_namespace(subject, expected_output):
    assert subject.needs_namespace == expected_output
