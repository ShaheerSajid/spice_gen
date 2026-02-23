import pytest
from spice_gen.model.primitives import PrimitiveKind, PRIMITIVE_REGISTRY


def test_nmos_spec():
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.NMOS]
    assert spec.port_order == ("D", "G", "S", "B")
    assert spec.spice_letter == "M"
    assert spec.value_param is None
    assert spec.model_param == "model_name"


def test_pmos_spec():
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.PMOS]
    assert spec.port_order == ("D", "G", "S", "B")
    assert spec.spice_letter == "M"


def test_bjt_spec():
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.NPN]
    assert spec.port_order == ("C", "B", "E")
    assert spec.spice_letter == "Q"


def test_resistor_spec():
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.R]
    assert spec.port_order == ("P", "N")
    assert spec.spice_letter == "R"
    assert spec.value_param == "value"
    assert spec.model_param is None


def test_diode_spec():
    spec = PRIMITIVE_REGISTRY[PrimitiveKind.DIODE]
    assert spec.port_order == ("A", "K")
    assert spec.spice_letter == "D"


def test_all_primitive_kinds_in_registry():
    for kind in PrimitiveKind:
        assert kind in PRIMITIVE_REGISTRY, f"{kind} missing from PRIMITIVE_REGISTRY"
