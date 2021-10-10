import pytest
from app.kubeseal import decode_base64_string, run_kubeseal, valid_k8s_name


@pytest.mark.parametrize(
    "value",
    ["abc", "l" + "o" * 60 + "ng", "some-1-too-check"],
)
def test_valid_k8s_name(value):
    # given a valid k8s-label-name
    # when valid_k8s_name is called on the label-name
    # then the label-name is returned unchanged
    assert valid_k8s_name(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "-something",
        "1a",
        "too-l" + "o" * 57 + "ng",
        "ähm",
        "_not-valid",
        "with spaces",
        " not-trimmed ",
        "no.dots.allowed",
        "no-special-chars-like/,#+%",
        "ends-on-dash-",
        "ends-on-digit-1",
    ],
)
def test_invalid_k8s_name(value):
    # given an invalid k8s-label-name
    # when valid_k8s_name is called on the label-name
    # then a ValueError is raised
    with pytest.raises(ValueError, match="Invalid k8s name"):
        valid_k8s_name(value)


def test_run_kubeseal_with_with_empty_string_namespace():
    # given an empty string secretNamespace
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_namespace was not given"):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "", "secretName")


def test_run_kubeseal_with_with_none_namespace():
    # given a None secretNamespace
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_namespace was not given"):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], None, "secretName")


def test_run_kubeseal_with_with_empty_string_secret_name():
    # given an empty string secretName
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_name was not given"):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", "")


def test_run_kubeseal_with_with_none_secret_name():
    # given a None secretName
    # when run_kubeseal is called
    # then raise ValueError
    with pytest.raises(ValueError, match="secret_name was not given"):
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", None)


def test_run_kubeseal_with_with_empty_secrets_list_but_otherwise_valid_inputs():
    # given an empty list
    # when run_kubeseal is called
    sealed_secrets = run_kubeseal([], "secretNamespace", "secretName")
    # then return empty list
    assert sealed_secrets == []


@pytest.mark.container()
@pytest.mark.cluster()
def test_run_kubeseal_with_cli():
    # given run test against cli with test cluster
    # when run_kubeseal is called
    # then return valid encrypted secret
    pass


@pytest.mark.cluster()
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
    with pytest.raises(
        ValueError, match="Input of cleartext_secrets was not a list of dicts."
    ):
        run_kubeseal(["this-should-be-a-dict-object"], "secretNamespace", "secretName")


@pytest.mark.container()
def test_run_kubeseal_without_k8s_cluster():
    # given kubeseal cli but no k8s cluster
    # when run_kubeseal is called
    # then raise RuntimeError
    with pytest.raises(RuntimeError) as error_cert_missing:
        run_kubeseal([{"key": "foo", "value": "YmFy"}], "secretNamespace", "secretName")
    assert "/kubeseal-webgui/cert/kubeseal-cert.pem: no such file or directory" in str(
        error_cert_missing
    )


@pytest.mark.parametrize(
    ("base64_input", "expected_output"),
    [("YWJjZGVm", "abcdef"), ("w6TDtsO8", "äöü"), ("LV8jIT8kwqc=", "-_#!?$§")],
)
def test_decode_base64_string(base64_input, expected_output):
    """
    Test decode_base64_string.

    Given a tuple with a Base64 input string and the corresponding output string.
    When calling decode_base64_string on input string.
    Then return the corresponding output string.
    """
    base64_encoded_string = decode_base64_string(base64_input)
    assert base64_encoded_string == expected_output
