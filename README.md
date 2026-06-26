# ⚔️ AuraBot — Throne and Liberty Dungeon Party Creator

A Discord bot for **Throne and Liberty** that lets players spin up parties and
recruit **Tanks 🛡️, Healers 💚 and DPS ⚔️** with a clean, interactive UI —
buttons to join/leave, a live roster that shows who picked what and what's
still needed, and a **start time** rendered with Discord's native timestamp
feature (so everyone sees it in their own timezone, counting down automatically).

---

## Features

- **`/create`** — opens a form to build a party:
  - choose the **activity** (open-world boss, dungeon, GvG, …) via autocomplete
  - choose a **difficulty / vibe**
  - set how many **Tank / Healer / DPS** slots you need (defaults to the classic
    1 / 1 / 4 six-stack)
  - add **notes** (CP requirements, voice, etc.)
  - set a **start time** — type `now`, `30m`, `1h30m`, `20:00`, `8:30pm`, **or
    paste a timestamp straight from [sesh.fyi/timestamp](https://sesh.fyi/timestamp/)**
    (`<t:1750005400:F>`) or a raw Unix epoch.
- **Live party card** posted to the channel with an `@here` ping, showing:
  - status (🟢 recruiting / ✅ full / 🔒 disbanded)
  - **start time** as `<t:…:F>` **and** a relative `<t:…:R>` countdown
  - a per-role roster — `✓` filled slots (with @mentions) and `○ open` slots
  - a **🔎 Looking for** line summarising what's still needed
- **Buttons** on every card: 🛡️ Tank · 💚 Healer · ⚔️ DPS · 🚪 Leave · 🔒 Disband
  - clicking a role **moves** you if you were already signed up as something else
  - **Disband** is restricted to the party leader (or a server moderator)
- **`/parties`** — lists every party still recruiting, what they need, and a jump link.
- **`/help`** — quick usage guide.
- **Persistent** — parties are saved to `data/parties.json`, and the buttons keep
  working after a bot restart.

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
cd aurabot-legal

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
bot.py                 # entry point, slash commands (/create, /parties, /help)
src/
  config.py            # roles, activity list, colours, difficulties
  party.py             # Party data model + JSON persistence
  embeds.py            # renders a Party into the rich message
  views.py             # buttons (PartyView) + the create-party modal
  timeparse.py         # parses start-time input (incl. sesh.fyi timestamps)
data/parties.json      # runtime state (git-ignored)
```

---

## Legal

[Privacy Policy](privacy.html) · [Terms of Service](terms.html)
