import pytest
from pydantic import ValidationError

from kubeseal_webgui_api.routers.models import Secret


def test_value_or_file_set_value():
    result = Secret(key="validation", value="value")

    assert result is not None


def test_value_or_file_set_file():
    result = Secret(key="validation", file="file")

    assert result is not None


def test_value_or_file_set_both():
    with pytest.raises(
        ValidationError, match="Only one field of 'value' or 'file' can be used"
    ):
        _ = Secret(key="validation", value="value", file="file")


def test_value_or_file_set_none():
    values = {}

    with pytest.raises(
        ValidationError, match="One field of 'value' or 'file' has to be set"
    ):
        _ = Secret(key="validation")


@pytest.mark.parametrize(
    ("base64_input", "expected_output"),
    [
        ("YWJjZGVm", "abcdef"),
        ("w6TDtsO8", "äöü"),
        ("LV8jIT8kwqc=", "-_#!?$§"),
    ],
)
def test_decode_value(base64_input, expected_output):
    subject = Secret(key="value", value=base64_input)

    assert subject.decode_value() == expected_output, f"Decoding '{base64_input}'"


@pytest.mark.parametrize(
    ("base64_input", "expected_output"),
    [
        ("YWJjZGVm", b"abcdef"),
        ("w6TDtsO8", "äöü".encode("utf-8")),
        ("LV8jIT8kwqc=", "-_#!?$§".encode("utf-8")),
    ],
)
def test_decode_file(base64_input, expected_output):
    subject = Secret(key="file", file=base64_input)

    assert subject.decode_file() == expected_output, f"Decoding '{base64_input}'"


def test_decode_value_none():
    subject = Secret(key="file", file="IA==")

    assert subject.decode_value() == ""


def test_decode_file_none():
    subject = Secret(key="value", value="IA==")

    assert subject.decode_file() == bytes()
