from __future__ import annotations

import json
import pathlib

import yaml

from ..schema.cell_schema import TopLevelSchema
from ..model.netlist import Netlist
from .builder import build_subckt_def


def load_file(path: str | pathlib.Path) -> Netlist:
    """
    Load a YAML or JSON topology file, validate it, and return a Netlist.

    Dispatches by file extension (.yaml/.yml -> YAML, .json -> JSON).
    Raises ValueError on unsupported extensions or schema violations.
    """
    path = pathlib.Path(path)
    raw = _read_raw(path)
    validated = TopLevelSchema.model_validate(raw)
    subckt_def = build_subckt_def(validated.cell)
    return Netlist(
        subckt_defs=[subckt_def],
        top_cell=subckt_def.name,
    )


def _read_raw(path: pathlib.Path) -> dict:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    if suffix == ".json":
        return json.loads(text)
    raise ValueError(
        f"Unsupported file extension '{suffix}'. Expected .yaml, .yml, or .json."
    )
