from __future__ import annotations

import pathlib

import yaml

from ..model.component import AnyComponent, PrimitiveComponent, SubcktInstance
from ..model.netlist import Netlist, PdkInclude, SubcktDef
from .pdk_config import ModelEntry, PdkConfig


def load_pdk(path: str | pathlib.Path) -> PdkConfig:
    """Load and validate a PDK YAML config file."""
    path = pathlib.Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PdkConfig.model_validate(raw)


def resolve(
    netlist: Netlist,
    pdk: PdkConfig,
    corner: str | None = None,
) -> Netlist:
    """
    Return a new Netlist with PDK model names resolved.

    For each PrimitiveComponent whose model_name matches a key in pdk.models:
      - is_subckt=True  → replaced with a SubcktInstance (X element)
      - is_subckt=False → model_name replaced with the PDK model name string

    Components whose model_name is not in the PDK mapping are left unchanged,
    preserving backward compatibility with explicit (non-logical) model names.

    A PdkInclude(.lib file + corner) is injected into the returned Netlist.
    """
    effective_corner = corner or pdk.default_corner
    new_defs = [_resolve_def(defn, pdk) for defn in netlist.subckt_defs]
    pdk_inc = PdkInclude(lib_file=str(pdk.lib_path), corner=effective_corner)
    return Netlist(
        subckt_defs=new_defs,
        top_cell=netlist.top_cell,
        pdk_includes=[pdk_inc],
    )


def _resolve_def(defn: SubcktDef, pdk: PdkConfig) -> SubcktDef:
    return SubcktDef(
        name=defn.name,
        ports=defn.ports,
        components=[_resolve_component(c, pdk) for c in defn.components],
        parameters=defn.parameters,
        includes=defn.includes,
    )


def _resolve_component(comp: AnyComponent, pdk: PdkConfig) -> AnyComponent:
    if not isinstance(comp, PrimitiveComponent) or comp.model_name is None:
        return comp

    entry = pdk.resolve_model(comp.model_name)
    if entry is None:
        return comp  # Unknown logical name — pass through unchanged

    if entry.is_subckt:
        return _to_subckt_instance(comp, entry)

    # Simple model name swap — keep as PrimitiveComponent
    return PrimitiveComponent(
        instance_name=comp.instance_name,
        kind=comp.kind,
        spec=comp.spec,
        connections=comp.connections,
        parameters=comp.parameters,
        model_name=entry.pdk_name,
        value=comp.value,
    )


def _to_subckt_instance(comp: PrimitiveComponent, entry: ModelEntry) -> SubcktInstance:
    """
    Convert a PrimitiveComponent into a SubcktInstance for subcircuit-wrapped
    PDK models (e.g. sky130 transistors).

    Nets are placed in the canonical SPICE port order defined by
    comp.spec.port_order, then assigned to the PDK's port names.
    Because SubcktInstance falls back to dict insertion order for external
    subcircuits, the insertion order of port_map must match the PDK's port
    declaration order.
    """
    # Nets in canonical port order (D→G→S→B for MOSFET, etc.)
    ordered_nets = [comp.connections[p] for p in comp.spec.port_order]

    # PDK port names: explicit from config, or lowercase canonical
    pdk_ports = entry.ports if entry.ports else [p.lower() for p in comp.spec.port_order]

    port_map = dict(zip(pdk_ports, ordered_nets))

    # Merge value into parameters for passive devices
    params = dict(comp.parameters)
    if comp.value is not None and comp.spec.value_param:
        params[comp.spec.value_param] = comp.value

    return SubcktInstance(
        instance_name=comp.instance_name,
        subckt_name=entry.pdk_name,
        port_map=port_map,
        parameters=params,
    )
