import pytest
from spice_gen.schema.cell_schema import TopLevelSchema
from spice_gen.parser.builder import build_subckt_def
from spice_gen.model.component import PrimitiveComponent, SubcktInstance
from spice_gen.model.primitives import PrimitiveKind, PRIMITIVE_REGISTRY


def _make_cell(components: list[dict], name="TEST", ports=None) -> dict:
    return {
        "cell": {
            "name": name,
            "ports": ports or ["A", "Z", "VDD", "VSS"],
            "components": components,
        }
    }


class TestPrimitiveBuilding:
    def test_nmos_ordered_nets(self):
        raw = _make_cell([{
            "id": "M1", "type": "primitive", "model": "nmos",
            "connections": {"D": "out", "G": "in", "S": "gnd", "B": "gnd"},
            "parameters": {"W": "1e-6", "L": "100e-9", "model_name": "nch"},
        }])
        defn = build_subckt_def(TopLevelSchema.model_validate(raw).cell)
        comp = defn.components[0]
        assert isinstance(comp, PrimitiveComponent)
        assert comp.ordered_nets() == ["out", "in", "gnd", "gnd"]

    def test_model_name_extracted(self):
        raw = _make_cell([{
            "id": "M1", "type": "primitive", "model": "pmos",
            "connections": {"D": "out", "G": "in", "S": "vdd", "B": "vdd"},
            "parameters": {"W": "2e-6", "L": "180e-9", "model_name": "pch"},
        }])
        defn = build_subckt_def(TopLevelSchema.model_validate(raw).cell)
        comp = defn.components[0]
        assert comp.model_name == "pch"
        assert "model_name" not in comp.parameters

    def test_resistor_value_extracted(self):
        raw = _make_cell([{
            "id": "R1", "type": "primitive", "model": "r",
            "connections": {"P": "a", "N": "b"},
            "parameters": {"value": "10000"},
        }])
        defn = build_subckt_def(TopLevelSchema.model_validate(raw).cell)
        comp = defn.components[0]
        assert comp.value == "10000"
        assert comp.model_name is None
        assert "value" not in comp.parameters

    def test_missing_port_raises(self):
        kind = PrimitiveKind.NMOS
        spec = PRIMITIVE_REGISTRY[kind]
        comp = PrimitiveComponent(
            instance_name="M1", kind=kind, spec=spec,
            connections={"D": "out", "G": "in", "S": "gnd"},  # B missing
            parameters={},
        )
        with pytest.raises(ValueError, match="missing required port"):
            comp.ordered_nets()


class TestSubcktBuilding:
    def test_subckt_instance(self):
        raw = _make_cell([{
            "id": "XINV", "type": "subckt", "model": "INV",
            "connections": {"A": "net_a", "Z": "net_z", "VDD": "VDD", "VSS": "VSS"},
            "parameters": {},
        }])
        defn = build_subckt_def(TopLevelSchema.model_validate(raw).cell)
        comp = defn.components[0]
        assert isinstance(comp, SubcktInstance)
        assert comp.subckt_name == "INV"
        assert comp.port_map["A"] == "net_a"


class TestSchemaValidation:
    def test_duplicate_id_raises(self):
        from pydantic import ValidationError
        raw = _make_cell([
            {"id": "M1", "type": "primitive", "model": "nmos",
             "connections": {"D": "a", "G": "b", "S": "c", "B": "c"}, "parameters": {}},
            {"id": "M1", "type": "primitive", "model": "pmos",
             "connections": {"D": "a", "G": "b", "S": "c", "B": "c"}, "parameters": {}},
        ])
        with pytest.raises(ValidationError, match="Duplicate component id"):
            TopLevelSchema.model_validate(raw)

    def test_invalid_primitive_model_raises(self):
        from pydantic import ValidationError
        raw = _make_cell([{
            "id": "M1", "type": "primitive", "model": "jfet",
            "connections": {"D": "a", "G": "b", "S": "c"}, "parameters": {},
        }])
        with pytest.raises(ValidationError, match="unknown primitive model"):
            TopLevelSchema.model_validate(raw)
