import pytest

from kubeseal_webgui_api.routers.models import is_blank, to_camel, valid_k8s_name


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "l" + "o" * 60 + "ng",
        "some-1-too-check",
        "ends-on-digit-1",
        "1starts-with-it",
        "some.dots.or_underscore",
        "long-" + "a" * 248,
    ],
)
def test_valid_k8s_name(value):
    # given a valid k8s-label-name
    # when valid_k8s_name is called on the label-name
    # then the label-name is returned unchanged
    assert valid_k8s_name(value) == True


@pytest.mark.parametrize(
    "value",
    [
        "",
        "-something",
        "too-l" + "o" * 247 + "ng",
        "ähm",
        "_not-valid",
        "with spaces",
        " not-trimmed ",
        "no-special-chars-like/,#+%",
        "ends-on-dash-",
        "Uppercase",
        "U",
        "uPPer",
    ],
)
def test_invalid_k8s_name(value):
    # given an invalid k8s-label-name
    # when valid_k8s_name is called on the label-name
    # then a ValueError is raised
    assert valid_k8s_name(value) == False


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\n",
        "\r",
        "\t",
        " \t\n\t ",
    ],
)
def test_is_blank(value):
    assert is_blank(value) == True


@pytest.mark.parametrize(
    "value",
    [
        "0",
        ".",
        "-",
        "_",
        " - ",
        ".  ",
        "  .",
        "\n\n.\n\n",
    ],
)
def test_is_not_blank(value):
    assert is_blank(value) == False


@pytest.mark.parametrize(
    ("value", "expected_output"),
    [
        ("hello", "hello"),
        ("hello_world", "helloWorld"),
        ("_hello_world", "HelloWorld"),
        ("hello_world_", "helloWorld"),
        ("hello__world", "helloWorld"),
    ],
)
def test_to_camel(value, expected_output):
    assert to_camel(value) == expected_output
