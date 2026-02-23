from .base import SpiceGenerator
from .spice3 import Spice3Generator
from .hspice import HspiceGenerator
from .ngspice import NgspiceGenerator

DIALECT_REGISTRY: dict[str, type[SpiceGenerator]] = {
    "spice3":  Spice3Generator,
    "hspice":  HspiceGenerator,
    "ngspice": NgspiceGenerator,
}


def get_generator(dialect: str) -> SpiceGenerator:
    """Return an instantiated generator for the given dialect name."""
    key = dialect.lower()
    if key not in DIALECT_REGISTRY:
        raise ValueError(
            f"Unknown dialect '{dialect}'. "
            f"Valid options: {sorted(DIALECT_REGISTRY)}"
        )
    return DIALECT_REGISTRY[key]()


__all__ = [
    "SpiceGenerator",
    "Spice3Generator",
    "HspiceGenerator",
    "NgspiceGenerator",
    "DIALECT_REGISTRY",
    "get_generator",
]
