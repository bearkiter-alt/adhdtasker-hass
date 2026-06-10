# ADHDTasker — Home Assistant integration

[![Validate](https://github.com/bearkiter-alt/adhdtasker-hass/actions/workflows/validate.yml/badge.svg)](https://github.com/bearkiter-alt/adhdtasker-hass/actions/workflows/validate.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

A native Home Assistant integration for [ADHDTasker](https://adhdtasker.com) — the family
chore-and-rewards app. It turns your board into real HA entities and services, over the same
family-scoped API documented at <https://adhdtasker.com/home-assistant.html>. No extra backend.

## What you get

**To-do entity** — `todo.adhdtasker_board`
- Every open task as a native To-do list. **Type** a new item → creates a task. **Tick** it
  off → completes it (awards points). **Rename** → updates the title. **Delete** → removes it.
  The assignee/points sit in each item's description.

**Sensors**
- `sensor.adhdtasker_open_tasks` — open count; attributes `todo`, `in_progress`,
  `pending_approval`, the full `tasks` list, and the `leaderboard`.
- `sensor.adhdtasker_pending_approval` — tasks waiting for a parent.
- `sensor.adhdtasker_<name>_points` / `_balance` — one pair per profile.
- `sensor.adhdtasker_last_event` — most recent webhook event (state = event, attrs = payload).

**Button** — `button.adhdtasker_refresh`.

**Services** — `adhdtasker.add_task`, `add_interrupt`, `claim_task`, `complete_task`,
`approve_task`, `ping`.

**Event** — `adhdtasker_event` fires on the bus for every webhook (secret stripped).

## Install

### HACS (custom repository)
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/bearkiter-alt/adhdtasker-hass`,
   category **Integration**.
2. Install **ADHDTasker**, then **restart Home Assistant**.
3. **Settings → Devices & Services → Add Integration → ADHDTasker**.
4. Paste your **API key** from the web app → **Manage → Inbound API**.

### Manual
Copy `custom_components/adhdtasker` into your HA `config/custom_components/`, restart, then add
the integration as above.

## Real-time push (optional)
Polling (default 60s, tunable in **Configure**) works alone. For instant updates, the setup
notification shows a **webhook URL** — paste it into the app → **Manage → Home Assistant** (or
enable a Nabu Casa cloudhook). Set a **shared secret** in the integration's options and the same
in the app to reject spoofed POSTs.

## Dashboard
A ready-to-paste Lovelace dashboard is in [`adhdtasker-dashboard.yaml`](adhdtasker-dashboard.yaml).

## Notes
- Points are awarded server-side on complete/approve; the integration never writes scores.
- Completing with no profile awards 0 points — use the `complete_task`/`approve_task` service
  with a `profile`, or assign/claim the task first, to credit a kid.
- Multiple families: add the integration once per family; services take an optional
  `config_entry_id` and the second family's entities get a `_2` suffix.

## License
[MIT](LICENSE).
