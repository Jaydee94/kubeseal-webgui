import base64
import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, root_validator, validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(word.capitalize() for word in tail)


def is_blank(value: Optional[str]) -> bool:
    return value is None or value.strip() == ""


def valid_k8s_name(value: str) -> bool:
    return re.match(r"^[a-z0-9]([a-z0-9_.-]{,251}[a-z0-9])?$", value) is not None


class WebGuiConfig(BaseModel):
    kubeseal_version: str

    class Config:
        alias_generator = to_camel
        allow_population_by_field_name = True


class KeyValuePair(BaseModel):
    key: str
    value: str


class Secret(BaseModel):
    key: str
    value: Optional[str] = None
    file: Optional[str] = None

    @root_validator
    @classmethod
    def value_or_file_set(cls, values):
        file, value = values.get("file"), values.get("value")
        if file and value:
            raise AssertionError("Only one field of 'value' or 'file' can be used")
        if file is None and value is None:
            raise AssertionError("One field of 'value' or 'file' has to be set")
        return values

    def decode_value(self) -> str:
        """Decode base64 ascii-encoded input."""
        if self.value is None:
            return ""

        data = self.value.encode("ascii")
        message = base64.b64decode(data)
        return message.decode("utf-8")

    def decode_file(self) -> bytes:
        """Decode base64 ascii-encoded input."""
        if self.file is None:
            return bytes()

        data = self.file.encode("ascii")
        return bytes(base64.b64decode(data))


class Scope(str, Enum):
    STRICT = "strict"
    CLUSTER_WIDE = "cluster-wide"
    NAMESPACE_WIDE = "namespace-wide"

    def needs_name(self):
        return self not in (Scope.CLUSTER_WIDE, Scope.NAMESPACE_WIDE)

    def needs_namespace(self):
        return self is not Scope.CLUSTER_WIDE


class Data(BaseModel):
    scope: Scope = Scope.STRICT
    secret: Optional[str]
    namespace: Optional[str]
    secrets: List[Secret]

    @validator("secret")
    @classmethod
    def secret_provided(cls, v, values, **kwargs) -> Optional[str]:
        if not values["scope"].needs_name():
            return None

        if is_blank(v):
            raise ValueError("must not be blank")

        if not valid_k8s_name(v):
            raise ValueError("must be a valid DNS identifier")

        return v.strip()

    @validator("namespace")
    @classmethod
    def namespace_provided(cls, v, values, **kwargs) -> Optional[str]:
        if not values["scope"].needs_namespace():
            return None

        if is_blank(v):
            raise ValueError("must not be blank")

        if not valid_k8s_name(v):
            raise ValueError("must be a valid DNS identifier")

        return v.strip()
