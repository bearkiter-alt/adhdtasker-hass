# ADHDTasker — Home Assistant integration

A native Home Assistant integration for [ADHDTasker](https://adhdtasker.com). It turns your
family chore board into real HA entities — a **To‑do list** for the board, **sensors** for
points/balances and counts — plus **services** to add/claim/complete tasks and ping the
family, and an optional **webhook** for real‑time push.

It talks to the same family‑scoped inbound API documented at
<https://adhdtasker.com/home-assistant.html> — no extra backend.

## What you get

> Entity IDs include your **family name** — replace `<family>` below with your family's slug
> (lowercase, e.g. the Muir family → `todo.muir_adhdtasker_board`). The exact ids are in
> **Developer Tools → States**.

**To‑do entity** — `todo.<family>_adhdtasker_board`
- Shows every open task. **Type a new item** → creates a task. **Tick one off** → completes
  it and awards its points. (There's no rename/delete API, so those are ignored.)

**Sensors**
- `sensor.<family>_adhdtasker_open_tasks` — open task count; attributes: `todo`, `in_progress`,
  `pending_approval`, the full `tasks` list (each task incl. its checkable `steps`), and the
  `leaderboard`.
- `sensor.<family>_adhdtasker_pending_approval` — tasks waiting for a parent.
- `sensor.<family>_adhdtasker_<name>_points` / `_balance` — one pair per profile (lifetime + bank).
- `sensor.<family>_adhdtasker_last_event` — the most recent webhook event (state = event name,
  attributes = payload).

**Button** — `button.<family>_adhdtasker_refresh` — pull fresh board state between polls.

**Services** — `adhdtasker.add_task`, `add_interrupt`, `claim_task`, `complete_task`, `ping`.

**Event** — `adhdtasker_event` fires on the HA bus for every webhook (secret stripped), so
you can drive announcements/lights from `task.completed`, `task.due`, `ping`, etc.

## Install

### Manual
1. Copy the `adhdtasker` folder into `config/custom_components/` on your HA host
   (so you have `config/custom_components/adhdtasker/manifest.json`).
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → ADHDTasker**.
4. Paste the **API key** from the web app → **Manage → Inbound API**. Done.

### HACS
This lives in a monorepo, so for HACS add it as a **custom repository** pointing at a repo
whose root contains `custom_components/adhdtasker/` (i.e. publish this folder as its own
repo), category *Integration*. Then install and restart.

## Optional: real‑time push (webhook)
Polling (default 60s, tunable in the integration's **Configure**) works on its own. For
instant updates, on first setup a notification shows a **webhook URL** — paste it into the web
app → **Manage → Home Assistant** (or enable a Nabu Casa cloudhook for it). Set a **shared
secret** in the integration's options and the same secret in the app to reject spoofed POSTs.

## Dashboard
A ready‑to‑paste Lovelace dashboard is in `ha/adhdtasker-dashboard.yaml` (To‑do card, gauge,
leaderboard, ping/refresh buttons).

## Notes / limits
- Points are awarded by the backend on `complete_task`; the integration never writes scores.
- Multiple families: each `Add Integration` makes its own device; services take an optional
  `config_entry_id`, and the second family's entities get a `_2` suffix.
- `complete`/`claim` accept a task **id** (from the sensor's `tasks` attribute) or a **title**.
