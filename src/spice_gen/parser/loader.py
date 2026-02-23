from __future__ import annotations

import json
import pathlib

import yaml

from ..schema.cell_schema import TopLevelSchema
from ..model.netlist import Netlist, SubcktDef
from .builder import build_subckt_def


def load_file(path: str | pathlib.Path) -> Netlist:
    """
    Load a YAML or JSON topology file, validate it, and return a Netlist.

    If the cell declares a `deps` list, each dep is loaded recursively first
    and its SubcktDefs are prepended in dependency order. This enables
    hierarchical composition: a cell can reference any dep's subcircuit by
    name and port ordering will be resolved automatically.

    Dep paths are resolved relative to the file that declares them.
    Circular dependencies raise ValueError.
    """
    path = pathlib.Path(path).resolve()
    all_defs = _load_recursive(path, loaded={}, in_progress=set())
    return Netlist(subckt_defs=all_defs, top_cell=all_defs[-1].name)


def _load_recursive(
    path: pathlib.Path,
    loaded: dict[pathlib.Path, list[SubcktDef]],
    in_progress: set[pathlib.Path],
) -> list[SubcktDef]:
    """
    Recursively load a cell file and all its deps.

    Returns a list of SubcktDefs in dependency order (deps first, cell last).
    Uses `loaded` to avoid reprocessing shared deps (diamond dependencies).
    Uses `in_progress` to detect cycles.
    """
    if path in loaded:
        return loaded[path]

    if path in in_progress:
        raise ValueError(
            f"Circular dependency detected while loading '{path}'. "
            "Check the 'deps' fields in your topology files."
        )

    in_progress.add(path)

    raw = _read_raw(path)
    validated = TopLevelSchema.model_validate(raw)

    # Collect SubcktDefs from all deps first, in order, without duplicates
    result: list[SubcktDef] = []
    seen_names: set[str] = set()

    for dep_str in validated.cell.deps:
        dep_path = (path.parent / dep_str).resolve()
        if not dep_path.exists():
            raise ValueError(
                f"Dep not found: '{dep_str}' (resolved to '{dep_path}') "
                f"declared in '{path}'"
            )
        dep_defs = _load_recursive(dep_path, loaded, in_progress)
        for defn in dep_defs:
            if defn.name not in seen_names:
                result.append(defn)
                seen_names.add(defn.name)

    # Append this cell's own SubcktDef last
    top_def = build_subckt_def(validated.cell)
    result.append(top_def)

    in_progress.discard(path)
    loaded[path] = result
    return result


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
