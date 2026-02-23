from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

VALID_PRIMITIVE_MODELS = frozenset({
    "nmos", "pmos", "npn", "pnp", "r", "c", "l", "vsrc", "isrc", "diode"
})


class ComponentSchema(BaseModel):
    id:          str
    type:        Literal["primitive", "subckt"]
    model:       str
    connections: dict[str, str]
    parameters:  dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_id_format(self) -> "ComponentSchema":
        if not _IDENT_RE.match(self.id):
            raise ValueError(
                f"Component id '{self.id}' is invalid. "
                "Use letters, digits, or underscores; must start with a letter or underscore."
            )
        return self

    @model_validator(mode="after")
    def _check_primitive_model(self) -> "ComponentSchema":
        if self.type == "primitive" and self.model not in VALID_PRIMITIVE_MODELS:
            raise ValueError(
                f"Component '{self.id}': unknown primitive model '{self.model}'. "
                f"Valid models: {sorted(VALID_PRIMITIVE_MODELS)}"
            )
        return self


class CellSchema(BaseModel):
    name:       str
    ports:      list[str] = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    includes:   list[str]      = Field(default_factory=list)
    deps:       list[str]      = Field(default_factory=list)
    components: list[ComponentSchema]

    @model_validator(mode="after")
    def _check_no_duplicate_ids(self) -> "CellSchema":
        seen: set[str] = set()
        for comp in self.components:
            if comp.id in seen:
                raise ValueError(f"Duplicate component id: '{comp.id}'")
            seen.add(comp.id)
        return self


class TopLevelSchema(BaseModel):
    cell: CellSchema
