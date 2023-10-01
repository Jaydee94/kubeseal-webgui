from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(word.capitalize() for word in tail)


class WebGuiConfig(BaseModel):
    kubeseal_version: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KeyValuePair(BaseModel):
    key: str
    value: str


class Secret(BaseModel):
    key: str
    value: Optional[str] = None
    file: Optional[str] = None

    @model_validator(mode="after")
    @classmethod
    def value_or_file_set(cls, secret: Any):
        file, value = secret.file, secret.value
        if file and value:
            raise AssertionError("Only one field of 'value' or 'file' can be used")
        if file is None and value is None:
            raise AssertionError("One field of 'value' or 'file' has to be set")
        return secret


class Scope(str, Enum):
    STRICT = "strict"
    CLUSTER_WIDE = "cluster-wide"
    NAMESPACE_WIDE = "namespace-wide"

    def needs_name(self):
        return self not in (Scope.CLUSTER_WIDE, Scope.NAMESPACE_WIDE)

    def needs_namespace(self):
        return self is not Scope.CLUSTER_WIDE


class Data(BaseModel):
    secret: Optional[str] = None
    namespace: Optional[str] = None
    secrets: List[Secret]
    scope: Optional[Scope] = None
