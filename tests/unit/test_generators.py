import pytest
from spice_gen.parser.loader import load_file
from spice_gen.generator import get_generator, DIALECT_REGISTRY
from spice_gen.model.netlist import Netlist, SubcktDef
from spice_gen.model.component import PrimitiveComponent
from spice_gen.model.primitives import PrimitiveKind, PRIMITIVE_REGISTRY

import pathlib

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _make_inverter_netlist() -> Netlist:
    nmos_spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
    pmos_spec = PRIMITIVE_REGISTRY[PrimitiveKind.PMOS]
    mn = PrimitiveComponent(
        instance_name="MN1", kind=PrimitiveKind.NMOS, spec=nmos_spec,
        connections={"D": "Z", "G": "A", "S": "VSS", "B": "VSS"},
        parameters={"W": "1e-6", "L": "180e-9"}, model_name="nch",
    )
    mp = PrimitiveComponent(
        instance_name="MP1", kind=PrimitiveKind.PMOS, spec=pmos_spec,
        connections={"D": "Z", "G": "A", "S": "VDD", "B": "VDD"},
        parameters={"W": "2e-6", "L": "180e-9"}, model_name="pch",
    )
    defn = SubcktDef(name="INV", ports=["A", "Z", "VDD", "VSS"], components=[mp, mn])
    return Netlist(subckt_defs=[defn], top_cell="INV")


class TestSpice3Generator:
    def test_header_contains_dialect(self):
        netlist = _make_inverter_netlist()
        out = get_generator("spice3").generate(netlist)
        assert "[spice3]" in out

    def test_subckt_header(self):
        netlist = _make_inverter_netlist()
        out = get_generator("spice3").generate(netlist)
        assert ".subckt INV A Z VDD VSS" in out

    def test_mosfet_port_order(self):
        netlist = _make_inverter_netlist()
        out = get_generator("spice3").generate(netlist)
        # PMOS: D G S B -> Z A VDD VDD
        assert "MMP1 Z A VDD VDD pch" in out
        # NMOS: D G S B -> Z A VSS VSS
        assert "MMN1 Z A VSS VSS nch" in out

    def test_ends_footer(self):
        netlist = _make_inverter_netlist()
        out = get_generator("spice3").generate(netlist)
        assert ".ends INV" in out

    def test_instance_params_format(self):
        netlist = _make_inverter_netlist()
        out = get_generator("spice3").generate(netlist)
        assert "W=1e-6" in out
        assert "L=180e-9" in out


class TestHspiceGenerator:
    def test_header_contains_dialect(self):
        netlist = _make_inverter_netlist()
        out = get_generator("hspice").generate(netlist)
        assert "[hspice]" in out

    def test_subckt_with_params_uses_PARAMS_keyword(self):
        nmos_spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
        comp = PrimitiveComponent(
            instance_name="M1", kind=PrimitiveKind.NMOS, spec=nmos_spec,
            connections={"D": "out", "G": "in", "S": "gnd", "B": "gnd"},
            parameters={}, model_name="nch",
        )
        defn = SubcktDef(
            name="CELL", ports=["IN", "OUT", "VDD", "GND"],
            components=[comp], parameters={"W": "1e-6"},
        )
        netlist = Netlist(subckt_defs=[defn], top_cell="CELL")
        out = get_generator("hspice").generate(netlist)
        assert "PARAMS:" in out


class TestNgspiceGenerator:
    def test_header_contains_dialect(self):
        netlist = _make_inverter_netlist()
        out = get_generator("ngspice").generate(netlist)
        assert "[ngspice]" in out

    def test_subckt_params_uses_lowercase_params(self):
        nmos_spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
        comp = PrimitiveComponent(
            instance_name="M1", kind=PrimitiveKind.NMOS, spec=nmos_spec,
            connections={"D": "out", "G": "in", "S": "gnd", "B": "gnd"},
            parameters={}, model_name="nch",
        )
        defn = SubcktDef(
            name="CELL", ports=["IN", "OUT", "VDD", "GND"],
            components=[comp], parameters={"IBIAS": "10e-6"},
        )
        netlist = Netlist(subckt_defs=[defn], top_cell="CELL")
        out = get_generator("ngspice").generate(netlist)
        assert "params:" in out

    def test_global_param_emitted(self):
        nmos_spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
        comp = PrimitiveComponent(
            instance_name="M1", kind=PrimitiveKind.NMOS, spec=nmos_spec,
            connections={"D": "out", "G": "in", "S": "gnd", "B": "gnd"},
            parameters={}, model_name="nch",
        )
        defn = SubcktDef(
            name="CELL", ports=["IN", "OUT"],
            components=[comp], parameters={"IBIAS": "10e-6"},
        )
        netlist = Netlist(subckt_defs=[defn], top_cell="CELL")
        out = get_generator("ngspice").generate(netlist)
        assert ".param IBIAS=10e-6" in out


class TestGetGenerator:
    def test_unknown_dialect_raises(self):
        with pytest.raises(ValueError, match="Unknown dialect"):
            get_generator("ltspice")

    def test_all_registered_dialects_instantiate(self):
        for dialect in DIALECT_REGISTRY:
            gen = get_generator(dialect)
            assert gen.DIALECT_NAME == dialect
