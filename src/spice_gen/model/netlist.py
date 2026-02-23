from __future__ import annotations

from dataclasses import dataclass, field

from .component import AnyComponent


@dataclass
class PdkInclude:
    """Represents a PDK .lib file + corner to be emitted before the subckt block."""

    lib_file: str   # Absolute path to the PDK .lib file
    corner:   str   # Corner section name (e.g. "tt", "ff", "ss")


@dataclass
class SubcktDef:
    """
    Represents a single .subckt block: its interface (ports) and contents (components).
    This is the primary container produced by the parser for each input file.
    """

    name:       str
    ports:      list[str]           # Ordered port list; order defines the .subckt line
    components: list[AnyComponent]
    parameters: dict[str, str] = field(default_factory=dict)
    includes:   list[str]      = field(default_factory=list)


@dataclass
class Netlist:
    """
    Top-level container. Holds one or more SubcktDef blocks in dependency order
    (dependencies before dependents).
    """

    subckt_defs:  list[SubcktDef]  = field(default_factory=list)
    top_cell:     str | None       = None
    pdk_includes: list[PdkInclude] = field(default_factory=list)

    def get_subckt(self, name: str) -> SubcktDef | None:
        """Look up a SubcktDef by name (used for port-order resolution)."""
        for defn in self.subckt_defs:
            if defn.name == name:
                return defn
        return None
