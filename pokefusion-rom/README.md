# 🧬 PokéFusion — a Pokémon FireRed fusion randomizer

A command-line tool that turns a **clean Pokémon FireRed (U) v1.0** ROM into a
**custom ROM hack** where every evolution family is *fused* with a random
partner — blending their **typings and skills** — and produces a coherent
**stage-1 → 2 → 3** evolution line. It outputs a patched `.gba` plus a
shareable **`.ips` patch**.

> **You must supply your own legally-owned ROM.** No copyrighted game data is
> included in or distributed by this project. The tool reads *your* ROM,
> rewrites its data tables, and writes a new file. Share the generated `.ips`
> patch, never the ROM.

---

## How the fusion works

For each evolution family in the game (e.g. `Bulbasaur → Ivysaur → Venusaur`):

* **Types** — the family's base type is blended with a random partner's primary
  type (deduped, capped at the Pokémon limit of 2). **Every stage shares this
  typing**, so the line stays coherent — a Grass/Electric stage-1 evolves into a
  Grass/Electric stage-2 and stage-3, never something off-theme.
* **Name** — each stage keeps its own root and gains a shared suffix from the
  partner, so the evolution line still reads like a family
  (`Bulbasle → Ivyssle → Venusle`).
* **Skills** — each stage is granted a signature move that matches its new
  typing, growing stronger as the line evolves.

Everything is driven by a **seed**, so a given `(ROM, seed)` always produces the
same hack — reproducible patches.

```
$ python -m pokefusion --rom firered.gba --dump-families | head
Detected 202 evolution families:
  BULBASAUR(Grass/Poison) → IVYSAUR(Grass/Poison) → VENUSAUR(Grass/Poison)
  CHARMANDER(Fire) → CHARMELEON(Fire) → CHARIZARD(Fire/Flying)
  ...

$ python -m pokefusion --rom firered.gba --seed 42 --out fused.gba --ips fused.ips
Fused 202 families (seed=42).
  [+ PLUSLE]   Bulbasle(Grass/Electric) → Ivyssle(Grass/Electric) → Venusle(Grass/Electric)
  [+ SLOWPOKE] Charmpoke(Fire/Water)    → ...                      → Charipoke(Fire/Water)
  ...
Wrote patched ROM → fused.gba
Wrote IPS patch  → fused.ips
```

---

## Usage

```bash
cd pokefusion-rom

# Generate a fused ROM + IPS patch (reproducible via --seed)
python -m pokefusion --rom path/to/firered.gba --seed 42 --out fused.gba --ips fused.ips

# Just inspect the evolution families the tool detects
python -m pokefusion --rom path/to/firered.gba --dump-families
```

| Flag | Meaning |
|---|---|
| `--rom PATH` | path to a clean FireRed (U) v1.0 ROM (**required**) |
| `--seed N` | RNG seed for reproducible fusions (default: random) |
| `--out PATH` | write the patched ROM here |
| `--ips PATH` | write an IPS patch here (diff vs. the input ROM) |
| `--legendary-evos` | **experimental** — give legendaries extra evolution stages (see below) |
| `--dump-families` | list detected families and exit, changing nothing |
| `--no-validate` | skip the ROM identity/MD5 check (not recommended) |

### Playing / sharing
* Load `fused.gba` in a GBA emulator (e.g. **mGBA**).
* To share legally, distribute **`fused.ips`** only. Others apply it to their own
  clean FireRed ROM with a patcher like **Flips** or **Lunar IPS**.

---

## Supported ROM

Pinned to **Pokémon FireRed (U) v1.0** — game code `BPRE`, MD5
`e26ee0d44e809351c8ce2d73c7400cdd`. The data-table offsets in
[`pokefusion/romspec.py`](pokefusion/romspec.py) were **verified by signature
scan** against this exact ROM (the commonly-cited base-stats offset `0x2547F4`
is actually wrong for it). On load the tool checks the game code + MD5 and runs
a self-check (species #1 must decode to `BULBASAUR`) so a wrong or dirty ROM
fails loudly instead of corrupting output.

## Limitations (by design of a binary patch)

* **No Fairy type** — Generation III only has 17 types; fusions never produce
  Fairy.
* **`--legendary-evos` is experimental.** A binary patch can't cleanly add brand
  new Pokédex species, so generated legendary evolutions reuse FireRed's unused
  species slots (252–276). Their **stats, types, name, evolution and learnset
  are wired up and valid**, but those slots have **no sprites/Pokédex data**, so
  they'll look glitchy in-game. Adding fully-fledged new species needs a
  decompilation build (pret `pokefirered`), which is out of scope here.
* Moves are injected by overwriting a species' earliest level-up moves (levels
  preserved), so learnsets never need to grow/relocate.

---

## Development

```bash
cd pokefusion-rom
pip install pytest
python -m pytest -q                # unit + synthetic-ROM tests (no ROM needed)

# Optional: run the integration suite against a real ROM
POKEFUSION_TEST_ROM=path/to/firered.gba python -m pytest -q tests/test_real_rom.py
```

Pure standard library (`struct`, `hashlib`, `argparse`) — no third-party runtime
dependencies. Layout:

```
pokefusion/
  romspec.py     # verified FireRed (U) v1.0 offsets, type ids, pointers
  gen3text.py    # Gen III text <-> str codec (species names)
  structs.py     # BaseStats (28B) + Evolution (8B) pack/unpack
  pokedata.py    # per-type move pools + name-fragment helpers
  fusion.py      # the fusion engine (pure logic, no IO)
  rom.py         # ROM load/validate + table read/write
  randomizer.py  # detect families -> fuse -> write back (seeded)
  patch.py       # IPS patch build/apply
  cli.py         # `python -m pokefusion`
```
