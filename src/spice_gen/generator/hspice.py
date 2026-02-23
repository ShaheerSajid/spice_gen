from .base import SpiceGenerator
from ..model.netlist import SubcktDef


class HspiceGenerator(SpiceGenerator):
    """
    Synopsys HSPICE dialect.

    - .subckt inline parameters use 'PARAMS:' keyword.
    - Instance parameters use 'PARAMS:' keyword.
    - Long lines are wrapped with '+' continuation at MAX_LINE_LEN characters.
    """

    DIALECT_NAME = "hspice"
    MAX_LINE_LEN = 132

    def _format_subckt_params(self, params: dict[str, str]) -> str:
        pairs = " ".join(f"{k}={v}" for k, v in params.items())
        return f"PARAMS: {pairs}"

    def _format_instance_params(self, params: dict[str, str]) -> str:
        pairs = " ".join(f"{k}={v}" for k, v in params.items())
        return f"PARAMS: {pairs}"

    def _format_subckt_header(self, defn: SubcktDef) -> str:
        line = super()._format_subckt_header(defn)
        return self._wrap_line(line)

    def _wrap_line(self, line: str) -> str:
        """Wrap lines exceeding MAX_LINE_LEN using HSPICE '+' continuation."""
        if len(line) <= self.MAX_LINE_LEN:
            return line
        words = line.split(" ")
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            # +2 for the "+ " prefix on continuation lines
            if len(current) + 1 + len(word) > self.MAX_LINE_LEN - 2:
                lines.append(current)
                current = "+ " + word
            else:
                current += " " + word
        lines.append(current)
        return "\n".join(lines)
