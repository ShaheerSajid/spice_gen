from __future__ import annotations

from ..schema.cell_schema import CellSchema, ComponentSchema
from ..model.component import AnyComponent, PrimitiveComponent, SubcktInstance
from ..model.netlist import SubcktDef
from ..model.primitives import PrimitiveKind, PRIMITIVE_REGISTRY


def build_subckt_def(cell: CellSchema) -> SubcktDef:
    """Convert a validated CellSchema into the internal SubcktDef model."""
    components: list[AnyComponent] = [_build_component(c) for c in cell.components]
    return SubcktDef(
        name=cell.name,
        ports=list(cell.ports),
        components=components,
        parameters={k: str(v) for k, v in cell.parameters.items()},
        includes=list(cell.includes),
    )


def _build_component(c: ComponentSchema) -> AnyComponent:
    if c.type == "primitive":
        return _build_primitive(c)
    return _build_subckt_instance(c)


def _build_primitive(c: ComponentSchema) -> PrimitiveComponent:
    kind = PrimitiveKind(c.model)
    spec = PRIMITIVE_REGISTRY[kind]

    # Convert all parameter values to strings for uniform handling downstream
    params: dict[str, str] = {k: str(v) for k, v in c.parameters.items()}

    # Extract the special value and model_name fields from the generic params dict
    value      = params.pop(spec.value_param, None)  if spec.value_param  else None
    model_name = params.pop(spec.model_param, None)  if spec.model_param  else None

    return PrimitiveComponent(
        instance_name=c.id,
        kind=kind,
        spec=spec,
        connections=dict(c.connections),
        parameters=params,
        model_name=model_name,
        value=value,
    )


def _build_subckt_instance(c: ComponentSchema) -> SubcktInstance:
    return SubcktInstance(
        instance_name=c.id,
        subckt_name=c.model,
        port_map=dict(c.connections),
        parameters={k: str(v) for k, v in c.parameters.items()},
    )
