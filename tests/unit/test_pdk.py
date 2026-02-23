import pathlib
import pytest
from pydantic import ValidationError

from spice_gen.pdk import load_pdk, resolve, PdkConfig, ModelEntry
from spice_gen.model.netlist import Netlist, SubcktDef, PdkInclude
from spice_gen.model.component import PrimitiveComponent, SubcktInstance
from spice_gen.model.primitives import PrimitiveKind, PRIMITIVE_REGISTRY

PDKS_DIR = pathlib.Path(__file__).parent.parent.parent / "pdks"


# ------------------------------------------------------------------ #
# PdkConfig validation
# ------------------------------------------------------------------ #

class TestPdkConfig:
    def test_sky130_loads(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        assert pdk.name == "sky130A"
        assert "tt" in pdk.corners
        assert pdk.default_corner == "tt"
        assert "nmos_1v8" in pdk.models

    def test_invalid_default_corner_raises(self):
        with pytest.raises(ValidationError, match="default_corner"):
            PdkConfig.model_validate({
                "name": "test", "path": "/tmp", "lib_file": "x.spice",
                "corners": ["tt", "ff"], "default_corner": "gg",
                "models": {},
            })

    def test_resolve_model_known(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        entry = pdk.resolve_model("nmos_1v8")
        assert entry is not None
        assert entry.pdk_name == "sky130_fd_pr__nfet_01v8"
        assert entry.is_subckt is True
        assert entry.ports == ["d", "g", "s", "b"]

    def test_resolve_model_unknown_returns_none(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        assert pdk.resolve_model("nonexistent_model") is None

    def test_lib_path(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        assert str(pdk.lib_path).endswith("sky130.lib.spice")


# ------------------------------------------------------------------ #
# Resolver: component transformation
# ------------------------------------------------------------------ #

def _make_nmos_comp(model_name="nmos_1v8") -> PrimitiveComponent:
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
    return PrimitiveComponent(
        instance_name="MN1",
        kind=PrimitiveKind.NMOS,
        spec=spec,
        connections={"D": "Z", "G": "A", "S": "VSS", "B": "VSS"},
        parameters={"W": "0.5", "L": "0.15", "nf": "1"},
        model_name=model_name,
    )


def _make_netlist(comp: PrimitiveComponent) -> Netlist:
    defn = SubcktDef(name="CELL", ports=["A", "Z", "VDD", "VSS"], components=[comp])
    return Netlist(subckt_defs=[defn], top_cell="CELL")


class TestResolver:
    def test_known_model_converted_to_subckt_instance(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("nmos_1v8"))
        resolved = resolve(netlist, pdk)
        comp = resolved.subckt_defs[0].components[0]
        assert isinstance(comp, SubcktInstance)
        assert comp.subckt_name == "sky130_fd_pr__nfet_01v8"
        assert comp.instance_name == "MN1"

    def test_port_map_nets_in_correct_order(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("nmos_1v8"))
        resolved = resolve(netlist, pdk)
        comp = resolved.subckt_defs[0].components[0]
        # port_map should map d→Z, g→A, s→VSS, b→VSS
        assert comp.port_map == {"d": "Z", "g": "A", "s": "VSS", "b": "VSS"}

    def test_parameters_preserved(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("nmos_1v8"))
        resolved = resolve(netlist, pdk)
        comp = resolved.subckt_defs[0].components[0]
        assert comp.parameters["W"] == "0.5"
        assert comp.parameters["L"] == "0.15"

    def test_unknown_model_passed_through(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("my_custom_model"))
        resolved = resolve(netlist, pdk)
        comp = resolved.subckt_defs[0].components[0]
        assert isinstance(comp, PrimitiveComponent)
        assert comp.model_name == "my_custom_model"

    def test_pdk_include_injected(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("nmos_1v8"))
        resolved = resolve(netlist, pdk)
        assert len(resolved.pdk_includes) == 1
        inc = resolved.pdk_includes[0]
        assert inc.corner == "tt"
        assert "sky130.lib.spice" in inc.lib_file

    def test_corner_override(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        netlist = _make_netlist(_make_nmos_comp("nmos_1v8"))
        resolved = resolve(netlist, pdk, corner="ff")
        assert resolved.pdk_includes[0].corner == "ff"

    def test_is_subckt_false_replaces_model_name_only(self):
        pdk = PdkConfig.model_validate({
            "name": "test", "path": "/tmp", "lib_file": "x.spice",
            "corners": ["tt"], "default_corner": "tt",
            "models": {
                "nmos_fake": {"pdk_name": "REAL_NMOS", "is_subckt": False}
            },
        })
        netlist = _make_netlist(_make_nmos_comp("nmos_fake"))
        resolved = resolve(netlist, pdk)
        comp = resolved.subckt_defs[0].components[0]
        assert isinstance(comp, PrimitiveComponent)
        assert comp.model_name == "REAL_NMOS"

    def test_original_netlist_not_mutated(self):
        pdk = load_pdk(PDKS_DIR / "sky130A.yaml")
        original_comp = _make_nmos_comp("nmos_1v8")
        netlist = _make_netlist(original_comp)
        resolve(netlist, pdk)
        # Original should still be PrimitiveComponent
        assert isinstance(netlist.subckt_defs[0].components[0], PrimitiveComponent)
