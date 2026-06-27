# Pre-built patches

These are ready-to-use **IPS patches** for the PokéFusion randomizer. They
contain only the hack's changes — **no copyrighted game data** — so you apply
them to your *own* legally-owned ROM.

| File | Build |
|---|---|
| `PokeFusion_FireRed_seed42.ips` | seed 42 · fused families + merged sprites + inverted shinies + **experimental** legendary evolutions |
| `PokeFusion_FireRed_seed42_no-legendary-evos.ips` | seed 42 · same, but **without** the experimental legendary evolutions (most stable) |

## How to apply

1. Get a clean **Pokémon FireRed (U) v1.0** ROM (MD5 `e26ee0d44e809351c8ce2d73c7400cdd`).
2. Apply a patch with [Flips](https://github.com/Alcaro/Flips) or Lunar IPS:
   - Flips → *Apply Patch* → pick the `.ips`, then your clean ROM → save the output `.gba`.
3. Open the resulting `.gba` in a GBA emulator (e.g. mGBA).

> A full pre-patched `.gba` is intentionally **not** distributed here — that
> would mean redistributing the copyrighted base game. The patch is the legal,
> standard way to share a ROM hack.

To build your own (any seed, options), see the [project README](../README.md).
