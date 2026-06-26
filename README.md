# 🎲 D20 — Throne and Liberty Dungeon Party Creator

A Discord bot for **Throne and Liberty** that lets players spin up parties and
recruit **Tanks 🛡️, Healers 💚 and DPS ⚔️** with a clean, interactive UI —
buttons to join/leave, a live roster that shows who picked what and what's
still needed, and a **start time** rendered with Discord's native timestamp
feature (so everyone sees it in their own timezone, counting down automatically).

---

## Features

### `/create` — start a party
Pick an **activity** via autocomplete — the full Throne and Liberty lineup: the
**Altar of Calanthia** 12-player raid, every **T1 / T2 / T3 co-op dungeon**
(Syleus's Abyss → Doomrot Grove), the **5500 CP** endgame dungeons (Hellfire
Crucible, Deathless Queen's Lair), **archbosses** (Bellandir, Tevent, Deluzhnoa,
Giant Cordy), field bosses, guild raids and PvP. Then, as command options:
- a **difficulty** (Normal / Elite / Epic for dungeons, Normal / Hard for raids)
- an optional **minimum Gear Score (CP)** — shown on the card and enforced on join
- an optional **voice channel link or ID** — pasted, rendered as a clickable 🔊 link

…and a quick form for the rest:
- **roles** — Tank / Healer / DPS counts (defaults to the classic `1 / 1 / 4`)
- a **start time** — `now`, `30m`, `1h30m`, `20:00`, `8:30pm`, a
  [sesh.fyi](https://sesh.fyi/timestamp/) timestamp (`<t:…>`) or a raw epoch
- **running for** — how long the party lasts (`2h`, `90m`); it shows an `ends in…`
  countdown and the bot **auto-closes** the party when the time is up
- **other dungeons** — extra dungeons the party will also run (comma-separated)
- **notes**

### The live party card
Posted with an `@here` ping and kept up to date in place:
- status + a **slot fill bar**, a compact meta row (difficulty · gear · voice · start)
- **start / end times** via Discord timestamps (each viewer's timezone, auto-countdown)
- a per-role roster — the 👑 **leader**, each member's **Gear Score**, and `+ open` slots
- a **🔎 Still need** summary and a **🎯 Also running** list of extra dungeons
- buttons: 🛡️ Tank · 💚 Healer · ⚔️ DPS · 🚪 **Leave** (any time) · 🔒 Disband (leader/mod)

### Joining
Clicking a role asks for your **Gear Score (CP)** in a popup; it's validated against
the party's minimum, then shown next to your name. Clicking another role moves you.

### Finding a group & the queue
- **`/lfg`** — find parties looking for members, optionally filtered by dungeon and/or role.
- **`/queue`** — queue for a specific dungeon **or 🎲 Any dungeon**: if a party is already
  looking you see it instantly, otherwise you're queued and **auto-added the moment a
  matching party forms** — open slots fill from the queue **longest-waited first**.
- **`/myqueue`** — see what you're queued for. **`/unqueue`** — leave the queue.
- **`/help`** — quick usage guide.

Parties and queues persist to `data/*.json`, and the buttons keep working after a restart.

---

## Examples

**Make a party** — pick the dungeon, difficulty, a min Gear Score and paste a voice link:

```
/create  activity:★★★ T3 · Chapel of Madness  difficulty:Epic  gear_score:3500  voice:https://discord.com/channels/123/456
```

…then the pop-up form fills in the rest:

```
Roles — Tank / Healer / DPS : 1 / 1 / 4
Start time (optional)       : 20:00
Running for (optional)      : 2h
Other dungeons (optional)   : ★★★ T3 · Rancorwood
Notes (optional)            : bring purifies, voice required
```

**The party card it posts** (updates live as people join):

```
Party Finder · led by Voyl
★★★ T3 · Chapel of Madness
🟢 Recruiting
▰▰▱▱▱▱  2/6
🎮 Epic · ⚡ 3,500+ CP · 🔊 #raid-voice
🕒 Today 20:00 · in 2 hours   ⏳ Running for 2h · ends in 4 hours

🛡️ Tank · 1/1        💚 Healer · 1/1       ⚔️ DPS · 0/4
👑 Voyl              Mendy · 3,800         + open
                                           + open
                                           + open
                                           + open

🎯 Also running
• ★★★ T3 · Rancorwood

🔎 Still need:  ⚔️ 4 DPS
📝 Notes: bring purifies, voice required
Party #A1B2C3 · tap a role below to join
[🛡️ Tank] [💚 Healer] [⚔️ DPS]   [🚪 Leave] [🔒 Disband]
```

Clicking **⚔️ DPS** asks for your Gear Score, then adds you: `✓ You joined as DPS (Gear Score: 4,100)`.

**Find a group:**

```
/lfg                                   → every party recruiting right now
/lfg  activity:★★★ T3 · Rancorwood     → only parties running Rancorwood
/lfg  role:Healer                      → only parties that still need a Healer
```

**Use the queue** (get auto-added when a party forms, longest-waited first):

```
/queue  activity:★★★ T3 · Rancorwood  role:DPS   → queue for that dungeon as DPS
/queue                                            → 🎲 Any dungeon, any role
/myqueue                                          → see what you're queued for
/unqueue                                          → leave the queue
```

---

## Setup

### 1. Create the bot application
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. **Bot** tab → **Add Bot** → copy the **token**.
3. **Installation / OAuth2** → invite the bot with the `bot` and
   `applications.commands` scopes. No privileged intents are required.

### 2. Configure & run
```bash
git clone <this-repo>
cd <repo-folder>

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env and paste your token
python bot.py
```

Setting `DISCORD_GUILD_ID` in `.env` makes the slash commands appear instantly
in that server while you test. Leaving it blank syncs globally (can take up to
an hour the first time).

---

## Project layout

```
bot.py                 # entry point, slash commands (/create /lfg /queue /myqueue /unqueue /help)
src/
  config.py            # roles, activity list, colours, difficulties
  party.py             # Party data model + JSON persistence
  queues.py            # party queue (QueueStore) + JSON persistence
  embeds.py            # renders a Party into the rich message
  views.py             # buttons (PartyView), create/join modals, queue notify
  timeparse.py         # parses start-time + duration input (incl. sesh.fyi)
data/parties.json      # party state   (git-ignored)
data/queue.json        # queue state   (git-ignored)
```

---

## Development & tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # unit + interaction-flow tests
python -m compileall bot.py src
```

CI runs the same checks on every push and pull request across Python 3.10–3.12
(see `.github/workflows/ci.yml`). Tests live in `tests/` and cover the start-time
parser, the party model + JSON persistence, embed rendering, and the full button
interaction flow (join / leave / disband) via mocked Discord interactions.

---

## Legal

[Privacy Policy](privacy.html) · [Terms of Service](terms.html)
