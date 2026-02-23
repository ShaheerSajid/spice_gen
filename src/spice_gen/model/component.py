from __future__ import annotations

from dataclasses import dataclass, field

from .primitives import PrimitiveKind, PrimitiveSpec


@dataclass
class PrimitiveComponent:
    """An instance of a SPICE primitive element (M, Q, R, C, L, V, I, D)."""

    instance_name: str
    kind:          PrimitiveKind
    spec:          PrimitiveSpec
    connections:   dict[str, str]   # port_name -> net_name
    parameters:    dict[str, str]   # remaining parameters (W, L, etc.)
    model_name:    str | None = None
    value:         str | None = None

    def ordered_nets(self) -> list[str]:
        """Return net names in canonical SPICE port order defined by spec.port_order."""
        try:
            return [self.connections[port] for port in self.spec.port_order]
        except KeyError as exc:
            raise ValueError(
                f"Component '{self.instance_name}' is missing required port {exc}. "
                f"Expected ports: {list(self.spec.port_order)}"
            ) from exc


@dataclass
class SubcktInstance:
    """An instance of a hierarchical subcircuit (.subckt reference)."""

    instance_name: str
    subckt_name:   str
    port_map:      dict[str, str]   # port_name -> net_name
    parameters:    dict[str, str] = field(default_factory=dict)

    def ordered_nets(self, port_order: list[str]) -> list[str]:
        """
        Return net names ordered by the referenced SubcktDef.ports list.
        port_order must come from the resolved SubcktDef at generation time.
        """
        try:
            return [self.port_map[port] for port in port_order]
        except KeyError as exc:
            raise ValueError(
                f"Subckt instance '{self.instance_name}' is missing port {exc} "
                f"(required by '{self.subckt_name}')"
            ) from exc


# Union type alias used throughout the codebase
AnyComponent = PrimitiveComponent | SubcktInstance
