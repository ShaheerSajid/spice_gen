"""Tests for hierarchical cell composition via the 'deps' field."""
import pathlib
import textwrap
import pytest

from spice_gen.parser.loader import load_file
from spice_gen.generator import get_generator

EXAMPLES = pathlib.Path(__file__).parent.parent.parent / "examples"
FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ------------------------------------------------------------------ #
# Helpers — write temporary YAML files for isolated tests
# ------------------------------------------------------------------ #

def _write(tmp_path: pathlib.Path, name: str, content: str) -> pathlib.Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


# ------------------------------------------------------------------ #
# Basic dep loading
# ------------------------------------------------------------------ #

class TestDepLoading:
    def test_dep_subcktdefs_come_before_top(self, tmp_path):
        _write(tmp_path, "inv.yaml", """
            cell:
              name: INV
              ports: [A, Z, VDD, VSS]
              components:
                - id: MN1
                  type: primitive
                  model: nmos
                  connections: {D: Z, G: A, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9, model_name: nch}
        """)
        _write(tmp_path, "buf.yaml", """
            cell:
              name: BUF
              ports: [A, Z, VDD, VSS]
              deps:
                - inv.yaml
              components:
                - id: XINV1
                  type: subckt
                  model: INV
                  connections: {A: A, Z: mid, VDD: VDD, VSS: VSS}
                - id: XINV2
                  type: subckt
                  model: INV
                  connections: {A: mid, Z: Z, VDD: VDD, VSS: VSS}
        """)
        netlist = load_file(tmp_path / "buf.yaml")
        assert len(netlist.subckt_defs) == 2
        assert netlist.subckt_defs[0].name == "INV"    # dep first
        assert netlist.subckt_defs[1].name == "BUF"    # top last
        assert netlist.top_cell == "BUF"

    def test_port_order_resolved_from_dep(self, tmp_path):
        _write(tmp_path, "inv.yaml", """
            cell:
              name: INV
              ports: [A, Z, VDD, VSS]
              components:
                - id: MN1
                  type: primitive
                  model: nmos
                  connections: {D: Z, G: A, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9, model_name: nch}
        """)
        _write(tmp_path, "buf.yaml", """
            cell:
              name: BUF
              ports: [IN, OUT, VDD, VSS]
              deps:
                - inv.yaml
              components:
                - id: XINV1
                  type: subckt
                  model: INV
                  connections: {A: IN, Z: mid, VDD: VDD, VSS: VSS}
                - id: XINV2
                  type: subckt
                  model: INV
                  connections: {A: mid, Z: OUT, VDD: VDD, VSS: VSS}
        """)
        netlist = load_file(tmp_path / "buf.yaml")
        out = get_generator("spice3").generate(netlist)
        # INV ports are [A, Z, VDD, VSS], so nets must appear in that order
        assert "XXINV1 IN mid VDD VSS INV" in out
        assert "XXINV2 mid OUT VDD VSS INV" in out

    def test_no_deps_still_works(self, tmp_path):
        _write(tmp_path, "inv.yaml", """
            cell:
              name: INV
              ports: [A, Z, VDD, VSS]
              components:
                - id: MN1
                  type: primitive
                  model: nmos
                  connections: {D: Z, G: A, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9, model_name: nch}
        """)
        netlist = load_file(tmp_path / "inv.yaml")
        assert len(netlist.subckt_defs) == 1
        assert netlist.top_cell == "INV"


# ------------------------------------------------------------------ #
# Diamond dependency (shared dep loaded only once)
# ------------------------------------------------------------------ #

class TestDiamondDependency:
    def test_shared_dep_emitted_once(self, tmp_path):
        _write(tmp_path, "inv.yaml", """
            cell:
              name: INV
              ports: [A, Z, VDD, VSS]
              components:
                - id: MN1
                  type: primitive
                  model: nmos
                  connections: {D: Z, G: A, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9, model_name: nch}
        """)
        _write(tmp_path, "buf.yaml", """
            cell:
              name: BUF
              ports: [A, Z, VDD, VSS]
              deps: [inv.yaml]
              components:
                - id: X1
                  type: subckt
                  model: INV
                  connections: {A: A, Z: mid, VDD: VDD, VSS: VSS}
                - id: X2
                  type: subckt
                  model: INV
                  connections: {A: mid, Z: Z, VDD: VDD, VSS: VSS}
        """)
        _write(tmp_path, "top.yaml", """
            cell:
              name: TOP
              ports: [IN, OUT, VDD, VSS]
              deps:
                - inv.yaml
                - buf.yaml
              components:
                - id: XBUF
                  type: subckt
                  model: BUF
                  connections: {A: IN, Z: OUT, VDD: VDD, VSS: VSS}
        """)
        netlist = load_file(tmp_path / "top.yaml")
        names = [d.name for d in netlist.subckt_defs]
        assert names.count("INV") == 1          # emitted exactly once
        assert names.index("INV") < names.index("BUF")
        assert names.index("BUF") < names.index("TOP")


# ------------------------------------------------------------------ #
# Cycle detection
# ------------------------------------------------------------------ #

class TestCycleDetection:
    def test_direct_cycle_raises(self, tmp_path):
        a = _write(tmp_path, "a.yaml", """
            cell:
              name: A
              ports: [X, VDD, VSS]
              deps: [b.yaml]
              components:
                - id: M1
                  type: primitive
                  model: nmos
                  connections: {D: X, G: X, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9}
        """)
        _write(tmp_path, "b.yaml", """
            cell:
              name: B
              ports: [X, VDD, VSS]
              deps: [a.yaml]
              components:
                - id: M1
                  type: primitive
                  model: nmos
                  connections: {D: X, G: X, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9}
        """)
        with pytest.raises(ValueError, match="Circular dependency"):
            load_file(a)


# ------------------------------------------------------------------ #
# Missing dep file
# ------------------------------------------------------------------ #

class TestMissingDep:
    def test_missing_dep_raises(self, tmp_path):
        _write(tmp_path, "top.yaml", """
            cell:
              name: TOP
              ports: [A, Z, VDD, VSS]
              deps: [does_not_exist.yaml]
              components:
                - id: M1
                  type: primitive
                  model: nmos
                  connections: {D: A, G: Z, S: VSS, B: VSS}
                  parameters: {W: 1e-6, L: 180e-9}
        """)
        with pytest.raises(ValueError, match="Dep not found"):
            load_file(tmp_path / "top.yaml")


# ------------------------------------------------------------------ #
# Integration: sky130 AOI21 example
# ------------------------------------------------------------------ #

class TestSky130Hierarchical:
    def test_aoi21_loads_all_three_subckt_defs(self):
        netlist = load_file(EXAMPLES / "sky130_aoi21.yaml")
        names = [d.name for d in netlist.subckt_defs]
        assert "NAND2_SKY130" in names
        assert "INV_SKY130" in names
        assert "AOI21_SKY130" in names
        # Deps appear before the cell that uses them
        assert names.index("NAND2_SKY130") < names.index("AOI21_SKY130")
        assert names.index("INV_SKY130") < names.index("AOI21_SKY130")
        assert netlist.top_cell == "AOI21_SKY130"

    def test_aoi21_ngspice_output_references_subcircuits(self):
        from spice_gen.pdk import load_pdk, resolve
        pdk = load_pdk(pathlib.Path(__file__).parent.parent.parent / "pdks" / "sky130A.yaml")
        netlist = load_file(EXAMPLES / "sky130_aoi21.yaml")
        resolved = resolve(netlist, pdk)
        out = get_generator("ngspice").generate(resolved)
        assert ".subckt AOI21_SKY130" in out
        assert ".subckt NAND2_SKY130" in out
        assert ".subckt INV_SKY130" in out
        assert "XXNAND" in out
        assert "XXNOR" in out

    def test_aoi21_port_order_from_dep_definition(self):
        from spice_gen.pdk import load_pdk, resolve
        pdk = load_pdk(pathlib.Path(__file__).parent.parent.parent / "pdks" / "sky130A.yaml")
        netlist = load_file(EXAMPLES / "sky130_aoi21.yaml")
        resolved = resolve(netlist, pdk)
        out = get_generator("ngspice").generate(resolved)
        # INV_SKY130 ports are [A, Z, VDD, VSS] — XNOR must follow that order
        assert "XXNOR C inv_out VDD VSS INV_SKY130" in out
        # NAND2_SKY130 ports are [A, B, Z, VDD, VSS]
        assert "XXNAND A B nand_out VDD VSS NAND2_SKY130" in out
