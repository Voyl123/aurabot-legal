"""pokefusion — a Pokémon FireRed (U) v1.0 fusion randomizer.

Reads a clean FireRed ROM, fuses each evolution family with a random partner
(blending types, skills and names coherently across all 3 evolution stages),
and writes out a patched ROM plus an IPS patch.
"""

from .rom import Rom, RomError
from .randomizer import run, detect_families, FusedLine
from .fusion import Mon, FusedStage, fuse_family, fuse_types
from .patch import build_ips, apply_ips

__all__ = [
    "Rom", "RomError", "run", "detect_families", "FusedLine",
    "Mon", "FusedStage", "fuse_family", "fuse_types",
    "build_ips", "apply_ips",
]

__version__ = "0.1.0"
