from .base import SpiceGenerator


class Spice3Generator(SpiceGenerator):
    """
    Berkeley SPICE3 dialect.

    - No inline parameter support on .subckt lines (emits a comment warning).
    - Instance parameters: space-separated key=value pairs.
    """

    DIALECT_NAME = "spice3"

    def _format_subckt_params(self, params: dict[str, str]) -> str:
        names = ", ".join(params.keys())
        return f"$ WARNING: SPICE3 does not support inline subckt params ({names})"

    def _format_instance_params(self, params: dict[str, str]) -> str:
        return " ".join(f"{k}={v}" for k, v in params.items())
