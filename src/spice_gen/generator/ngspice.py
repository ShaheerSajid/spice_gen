from .base import SpiceGenerator
from ..model.netlist import Netlist


class NgspiceGenerator(SpiceGenerator):
    """
    ngspice dialect (open-source SPICE3 superset).

    - .subckt inline parameters use 'params:' keyword.
    - Instance parameters: space-separated key=value pairs.
    - Top-level cell parameters emitted as a global .param directive.
    """

    DIALECT_NAME = "ngspice"

    def _format_subckt_params(self, params: dict[str, str]) -> str:
        pairs = " ".join(f"{k}={v}" for k, v in params.items())
        return f"params: {pairs}"

    def _format_instance_params(self, params: dict[str, str]) -> str:
        return " ".join(f"{k}={v}" for k, v in params.items())

    def _format_header(self, netlist: Netlist) -> str:
        base = super()._format_header(netlist)
        top = netlist.subckt_defs[0] if netlist.subckt_defs else None
        if top and top.parameters:
            param_str = " ".join(f"{k}={v}" for k, v in top.parameters.items())
            return base + f"\n.param {param_str}"
        return base
