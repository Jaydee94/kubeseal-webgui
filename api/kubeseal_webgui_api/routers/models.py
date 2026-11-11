from enum import Enum
from typing import List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(word.capitalize() for word in tail)


class WebGuiConfig(BaseModel):
    kubeseal_version: str
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KeyValuePair(BaseModel):
    key: str
    value: str


class ExistingSealedSecret(BaseModel):
    name: str
    keys: List[str]


class Secret(BaseModel):
    key: str
    value: Optional[str] = None
    file: Optional[str] = None

    @model_validator(mode="after")
    def value_or_file_set(self: Self) -> Self:
        if self.file is not None and self.value is not None:
            raise ValueError("Only one field of 'value' or 'file' can be used")
        if self.file is None and self.value is None:
            raise ValueError("One field of 'value' or 'file' has to be set")
        return self


class Scope(str, Enum):
    STRICT = "strict"
    CLUSTER_WIDE = "cluster-wide"
    NAMESPACE_WIDE = "namespace-wide"

    def needs_name(self: Self) -> bool:
        return self not in (Scope.CLUSTER_WIDE, Scope.NAMESPACE_WIDE)

    def needs_namespace(self: Self) -> bool:
        return self is not Scope.CLUSTER_WIDE


class Data(BaseModel):
    # The name of the secret, not a secret value. The JSON key stays "secret";
    # the attribute is called `name` so that neither readers nor static
    # analysis mistake it for sensitive data (the values live in `secrets`).
    name: Optional[str] = Field(default=None, alias="secret")
    namespace: Optional[str] = None
    secrets: List[Secret]
    scope: Optional[Scope] = None
