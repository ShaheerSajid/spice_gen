"""End-to-end integration tests: YAML file -> SPICE text."""
import pathlib
import pytest
from spice_gen.parser.loader import load_file
from spice_gen.generator import get_generator

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
EXAMPLES = pathlib.Path(__file__).parent.parent.parent / "examples"


@pytest.mark.parametrize("dialect", ["spice3", "hspice", "ngspice"])
def test_inverter_generates_without_error(dialect):
    netlist = load_file(FIXTURES / "inverter.yaml")
    out = get_generator(dialect).generate(netlist)
    assert ".subckt INV" in out
    assert ".ends INV" in out
    # Both transistors present
    assert "MMP1" in out
    assert "MMN1" in out


@pytest.mark.parametrize("dialect", ["spice3", "hspice", "ngspice"])
def test_nand2_generates_without_error(dialect):
    netlist = load_file(EXAMPLES / "nand2.yaml")
    out = get_generator(dialect).generate(netlist)
    assert ".subckt NAND2" in out
    assert ".ends NAND2" in out
    # Four transistors
    assert "MMP1" in out
    assert "MMP2" in out
    assert "MMN1" in out
    assert "MMN2" in out
    # Internal node
    assert "mid" in out


@pytest.mark.parametrize("dialect", ["spice3", "hspice", "ngspice"])
def test_opamp_snippet_generates_without_error(dialect):
    netlist = load_file(EXAMPLES / "opamp_snippet.yaml")
    out = get_generator(dialect).generate(netlist)
    assert ".subckt DIFF_PAIR" in out
    assert ".ends DIFF_PAIR" in out
    # Subcircuit instance
    assert "XXBIAS" in out
    assert "BIAS_GEN" in out


def test_inverter_port_order_spice3():
    netlist = load_file(FIXTURES / "inverter.yaml")
    out = get_generator("spice3").generate(netlist)
    # PMOS M line: D G S B = Z A VDD VDD
    assert "MMP1 Z A VDD VDD pch" in out
    # NMOS M line: D G S B = Z A VSS VSS
    assert "MMN1 Z A VSS VSS nch" in out


def test_nand2_internal_net_spice3():
    netlist = load_file(EXAMPLES / "nand2.yaml")
    out = get_generator("spice3").generate(netlist)
    # MN1 source connects to 'mid', MN2 drain connects to 'mid'
    assert "mid" in out


def test_opamp_isrc_line_spice3():
    netlist = load_file(EXAMPLES / "opamp_snippet.yaml")
    out = get_generator("spice3").generate(netlist)
    # I source: P N value  -> TAIL VSS {IBIAS}
    assert "IITAIL TAIL VSS {IBIAS}" in out


def test_opamp_resistor_line_spice3():
    netlist = load_file(EXAMPLES / "opamp_snippet.yaml")
    out = get_generator("spice3").generate(netlist)
    assert "RR_LOAD1 VDD OUT_N 10000" in out


def test_opamp_capacitor_line_spice3():
    netlist = load_file(EXAMPLES / "opamp_snippet.yaml")
    out = get_generator("spice3").generate(netlist)
    assert "CC_COMP OUT_P OUT_N 1e-12" in out
