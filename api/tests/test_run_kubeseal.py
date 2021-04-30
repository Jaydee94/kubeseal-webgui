from app.kubeseal import run_kubeseal
import pytest


def test_run_kubeseal_with_with_empty_string_namespace():
    # given an empty string secretNamespace
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "", "secretName")


def test_run_kubeseal_with_with_none_namespace():
    # given a None secretNamespace
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], None, "secretName")


def test_run_kubeseal_with_with_empty_string_secret_name():
    # given an empty string secretName
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", "")


def test_run_kubeseal_with_with_none_secret_name():
    # given a None secretName
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", None)


def test_run_kubeseal_with_with_empty_secrets_list_but_otherwise_valid_inputs():
    # given an empty list
    # when run_kubeseal is called
    sealedSecrets = run_kubeseal([], "secretNamespace", "secretName")
    # then return empty list
    assert sealedSecrets == []


@pytest.mark.container
@pytest.mark.cluster
def test_run_kubeseal_with_cli():
    # given run test against cli with test cluster
    # when run_kubeseal is called
    # then return valid encrypted secret
    pass


@pytest.mark.cluster
def test_run_kubeseal_without_cli():
    # given k8s cluster but no kubeseal cli
    # when run_kubeseal is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", "secretName")


def test_run_kubeseal_with_invalid_secrets_list_but_otherwise_valid_inputs():
    # given a secret list with string element
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError):
        run_kubeseal(["this-should-be-a-dict-object"], "secretNamespace", "secretName")


@pytest.mark.container
def test_run_kubeseal_without_k8s_cluster():
    # given kubeseal cli but no k8s cluster
    # when run_kubeseal is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError) as error_cert_missing:
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", "secretName")
    assert "/kubeseal-webgui/cert/kubeseal-cert.pem: no such file or directory" in str(
        error_cert_missing
    )
