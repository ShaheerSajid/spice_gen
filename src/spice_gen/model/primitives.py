from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PrimitiveKind(str, Enum):
    """Canonical primitive device types. Values match the 'model' field in YAML."""
    NMOS  = "nmos"
    PMOS  = "pmos"
    NPN   = "npn"
    PNP   = "pnp"
    R     = "r"
    C     = "c"
    L     = "l"
    VSRC  = "vsrc"
    ISRC  = "isrc"
    DIODE = "diode"


@dataclass(frozen=True)
class PrimitiveSpec:
    """
    Describes how to emit a SPICE line for a given primitive type.

    port_order:   Canonical port names in SPICE positional order.
    spice_letter: SPICE element prefix letter.
    value_param:  Key in 'parameters' that becomes the positional value field
                  (e.g. resistance for R). None for transistors.
    model_param:  Key in 'parameters' that is the device model card name.
                  None for passives/sources.
    """
    port_order:   tuple[str, ...]
    spice_letter: str
    value_param:  str | None = None
    model_param:  str | None = "model_name"


# Single source of truth for all port-ordering rules.
PRIMITIVE_REGISTRY: dict[PrimitiveKind, PrimitiveSpec] = {
    PrimitiveKind.NMOS: PrimitiveSpec(
        port_order=("D", "G", "S", "B"),
        spice_letter="M",
        value_param=None,
        model_param="model_name",
    ),
    PrimitiveKind.PMOS: PrimitiveSpec(
        port_order=("D", "G", "S", "B"),
        spice_letter="M",
        value_param=None,
        model_param="model_name",
    ),
    PrimitiveKind.NPN: PrimitiveSpec(
        port_order=("C", "B", "E"),
        spice_letter="Q",
        value_param=None,
        model_param="model_name",
    ),
    PrimitiveKind.PNP: PrimitiveSpec(
        port_order=("C", "B", "E"),
        spice_letter="Q",
        value_param=None,
        model_param="model_name",
    ),
    PrimitiveKind.R: PrimitiveSpec(
        port_order=("P", "N"),
        spice_letter="R",
        value_param="value",
        model_param=None,
    ),
    PrimitiveKind.C: PrimitiveSpec(
        port_order=("P", "N"),
        spice_letter="C",
        value_param="value",
        model_param=None,
    ),
    PrimitiveKind.L: PrimitiveSpec(
        port_order=("P", "N"),
        spice_letter="L",
        value_param="value",
        model_param=None,
    ),
    PrimitiveKind.VSRC: PrimitiveSpec(
        port_order=("P", "N"),
        spice_letter="V",
        value_param="value",
        model_param=None,
    ),
    PrimitiveKind.ISRC: PrimitiveSpec(
        port_order=("P", "N"),
        spice_letter="I",
        value_param="value",
        model_param=None,
    ),
    PrimitiveKind.DIODE: PrimitiveSpec(
        port_order=("A", "K"),
        spice_letter="D",
        value_param=None,
        model_param="model_name",
    ),
}
