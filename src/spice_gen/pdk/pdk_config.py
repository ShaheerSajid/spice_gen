from __future__ import annotations

import pathlib
from typing import Optional

from pydantic import BaseModel, model_validator


class ModelEntry(BaseModel):
    """Describes how a logical device name maps to a PDK model."""

    pdk_name:  str                   # PDK subcircuit/model name
    is_subckt: bool = True           # True → emit X element; False → native M/Q/D
    ports:     Optional[list[str]] = None  # PDK port order; None → use canonical


class PdkConfig(BaseModel):
    """Configuration for a process design kit."""

    name:           str
    description:    str = ""
    path:           str              # Base path to PDK installation
    lib_file:       str              # Path to .lib file, relative to `path`
    corners:        list[str]
    default_corner: str
    models:         dict[str, ModelEntry]  # logical_name → ModelEntry

    @model_validator(mode="after")
    def _check_default_corner(self) -> "PdkConfig":
        if self.default_corner not in self.corners:
            raise ValueError(
                f"default_corner '{self.default_corner}' is not in corners list: "
                f"{self.corners}"
            )
        return self

    def resolve_model(self, logical_name: str) -> ModelEntry | None:
        """Return the ModelEntry for a logical name, or None if not mapped."""
        return self.models.get(logical_name)

    @property
    def lib_path(self) -> pathlib.Path:
        """Absolute path to the PDK .lib file."""
        return pathlib.Path(self.path) / self.lib_file
