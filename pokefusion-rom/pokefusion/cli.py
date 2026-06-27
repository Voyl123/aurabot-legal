"""Command-line interface: ``python -m pokefusion``.

Examples
--------
    # Generate a fused ROM + IPS patch, reproducible via the seed
    python -m pokefusion --rom firered.gba --seed 42 --out fused.gba --ips fused.ips

    # Inspect detected evolution families without writing anything
    python -m pokefusion --rom firered.gba --dump-families
"""

from __future__ import annotations

import argparse
import sys

from . import romspec
from .patch import build_ips
from .randomizer import detect_families, run
from .rom import Rom, RomError


def _type_names(type_ids: tuple[int, ...]) -> str:
    return "/".join(romspec.TYPE_NAMES.get(t, f"?{t}") for t in type_ids)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pokefusion",
        description="Fuse every evolution family in a Pokémon FireRed (U) v1.0 ROM.",
    )
    p.add_argument("--rom", required=True, help="path to a clean FireRed (U) v1.0 ROM")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed for reproducible fusions (default: random)")
    p.add_argument("--out", help="write the patched ROM here (e.g. fused.gba)")
    p.add_argument("--ips", help="write an IPS patch here (e.g. fused.ips)")
    p.add_argument("--legendary-evos", action="store_true",
                   help="EXPERIMENTAL: give legendaries extra evolution stages "
                        "in unused species slots (graphics will be glitchy)")
    p.add_argument("--dump-families", action="store_true",
                   help="list detected evolution families and exit (no changes)")
    p.add_argument("--no-validate", action="store_true",
                   help="skip ROM identity/MD5 validation (not recommended)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        rom = Rom.load(args.rom, validate=not args.no_validate)
    except (OSError, RomError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dump_families:
        families = detect_families(rom)
        print(f"Detected {len(families)} evolution families:")
        for fam in families:
            chain = " → ".join(f"{m.name}({_type_names(m.types)})" for m in fam)
            print(f"  {chain}")
        return 0

    original = bytes(rom.data)
    report = run(rom, seed=args.seed, legendary_evos=args.legendary_evos)

    print(f"Fused {len(report)} families (seed={args.seed}).")
    for line in report[:12]:  # a short preview
        chain = " → ".join(f"{s.name}({_type_names(s.types)})" for s in line.stages)
        print(f"  [+ {line.partner}] {chain}")
        for slot, name, types in line.extra_evos:
            print(f"        ⤷ new evo: {name}({_type_names(types)}) in slot {slot}")
    if len(report) > 12:
        print(f"  … and {len(report) - 12} more.")

    if args.out:
        rom.save(args.out)
        print(f"Wrote patched ROM → {args.out}")
    if args.ips:
        with open(args.ips, "wb") as fh:
            fh.write(build_ips(original, bytes(rom.data)))
        print(f"Wrote IPS patch  → {args.ips}")
    if not args.out and not args.ips:
        print("(no --out/--ips given; nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
