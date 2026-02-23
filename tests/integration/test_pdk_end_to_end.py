"""End-to-end integration tests for PDK-aware netlist generation."""
import pathlib
import pytest

from spice_gen.parser.loader import load_file
from spice_gen.pdk import load_pdk, resolve
from spice_gen.generator import get_generator

EXAMPLES = pathlib.Path(__file__).parent.parent.parent / "examples"
PDKS    = pathlib.Path(__file__).parent.parent.parent / "pdks"


@pytest.fixture(scope="module")
def sky130_pdk():
    return load_pdk(PDKS / "sky130A.yaml")


@pytest.fixture(scope="module")
def sky130_inverter_netlist(sky130_pdk):
    netlist = load_file(EXAMPLES / "sky130_inverter.yaml")
    return resolve(netlist, sky130_pdk)


class TestSky130InverterNgspice:
    def test_lib_directive_present(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        assert '.lib "' in out
        assert 'sky130.lib.spice" tt' in out

    def test_x_elements_not_m_elements(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        assert "XMP1" in out
        assert "XMN1" in out
        assert "MMP1" not in out
        assert "MMN1" not in out

    def test_correct_pdk_model_names(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        assert "sky130_fd_pr__pfet_01v8" in out
        assert "sky130_fd_pr__nfet_01v8" in out

    def test_port_order_d_g_s_b(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        # PMOS: d=Z g=A s=VDD b=VDD → XMP1 Z A VDD VDD
        assert "XMP1 Z A VDD VDD sky130_fd_pr__pfet_01v8" in out
        # NMOS: d=Z g=A s=VSS b=VSS → XMN1 Z A VSS VSS
        assert "XMN1 Z A VSS VSS sky130_fd_pr__nfet_01v8" in out

    def test_parameters_present(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        assert "W=1.0" in out
        assert "L=0.15" in out
        assert "nf=1" in out

    def test_subckt_block_present(self, sky130_inverter_netlist):
        out = get_generator("ngspice").generate(sky130_inverter_netlist)
        assert ".subckt INV_SKY130 A Z VDD VSS" in out
        assert ".ends INV_SKY130" in out


class TestSky130InverterSpice3:
    def test_include_not_lib(self, sky130_inverter_netlist):
        out = get_generator("spice3").generate(sky130_inverter_netlist)
        # SPICE3 uses .include; the .lib directive syntax ('.lib "...") must not appear
        assert ".include" in out
        assert '\n.lib "' not in out

    def test_x_elements_present(self, sky130_inverter_netlist):
        out = get_generator("spice3").generate(sky130_inverter_netlist)
        assert "XMP1" in out
        assert "XMN1" in out


class TestSky130InverterHspice:
    def test_lib_directive_present(self, sky130_inverter_netlist):
        out = get_generator("hspice").generate(sky130_inverter_netlist)
        assert '.lib "' in out

    def test_params_keyword_on_instance(self, sky130_inverter_netlist):
        out = get_generator("hspice").generate(sky130_inverter_netlist)
        assert "PARAMS:" in out


class TestCornerSelection:
    def test_ff_corner_in_lib_line(self, sky130_pdk):
        netlist = load_file(EXAMPLES / "sky130_inverter.yaml")
        resolved = resolve(netlist, sky130_pdk, corner="ff")
        out = get_generator("ngspice").generate(resolved)
        assert 'sky130.lib.spice" ff' in out

    def test_default_corner_is_tt(self, sky130_pdk):
        netlist = load_file(EXAMPLES / "sky130_inverter.yaml")
        resolved = resolve(netlist, sky130_pdk)
        out = get_generator("ngspice").generate(resolved)
        assert 'sky130.lib.spice" tt' in out


class TestNoPdkBackwardCompat:
    def test_existing_examples_unaffected(self):
        # Verify existing examples still work without --pdk
        netlist = load_file(EXAMPLES / "inverter.yaml")
        out = get_generator("spice3").generate(netlist)
        assert "MMP1" in out
        assert ".lib" not in out
        assert ".include" not in out
