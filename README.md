# ADHDTasker — Home Assistant integration

[![Validate](https://github.com/bearkiter-alt/adhdtasker-hass/actions/workflows/validate.yml/badge.svg)](https://github.com/bearkiter-alt/adhdtasker-hass/actions/workflows/validate.yml)
[![hacs](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)

A native Home Assistant integration for [ADHDTasker](https://adhdtasker.com) — the family
chore-and-rewards app. It turns your board into real HA entities and services, over the same
family-scoped API documented at <https://adhdtasker.com/home-assistant.html>. No extra backend.

## What you get

> Entity IDs include your **family name** — replace `<family>` below with your family's slug
> (lowercase, e.g. the Muir family → `todo.muir_adhdtasker_board`). The exact ids are in
> **Developer Tools → States**.

**To-do entity** — `todo.<family>_adhdtasker_board`
- Every open task as a native To-do list. **Type** a new item → creates a task. **Tick** it
  off → completes it (awards points). **Rename** → updates the title. **Delete** → removes it.
  The assignee/points sit in each item's description.

**Sensors**
- `sensor.<family>_adhdtasker_open_tasks` — open count; attributes `todo`, `in_progress`,
  `pending_approval`, the full `tasks` list (each task incl. its checkable `steps`), and the
  `leaderboard`. The example dashboard renders tasks as tap-through links with their steps
  as read-only ☐/☑.
- `sensor.<family>_adhdtasker_pending_approval` — tasks waiting for a parent.
- `sensor.<family>_adhdtasker_<name>_points` / `_balance` — one pair per profile.
- `sensor.<family>_adhdtasker_last_event` — most recent webhook event (state = event, attrs = payload).

**Button** — `button.<family>_adhdtasker_refresh`.

**Services** — `adhdtasker.add_task`, `add_interrupt`, `claim_task`, `complete_task`,
`approve_task`, `ping`.

**Event** — `adhdtasker_event` fires on the bus for every webhook (secret stripped).

Every event carries the same envelope:

| Field | What |
|---|---|
| `event` | `task.added`, `task.proposed`, `interrupt.added`, `task.claimed`, `task.submitted`, `task.completed`, `task.approved`, `task.due`, `reward.requested`, `ping`, `test` |
| `previous_status` | status *before* the change — `""` when nothing moved (a create, or a due reminder) |
| `status` | status after it |
| `profile` | `{ name }` — the person the chore belongs to / who gets the credit |
| `actor` | `{ id, name, role }` — **who caused it**, which is often someone else |
| `task` | `{ id, title, points, type, status }` |

`actor` is not the same as `profile`: when a parent approves a kid's chore, the parent is the
`actor` and the kid is the `profile`. Both are always objects, so `trigger.event.data.actor.name`
is safe to read unguarded; empty strings mean no nameable person did it — a due reminder is the
clock, and an inbound `/api` call is an automation. `actor` is stamped server-side and a child
cannot forge it (the security rules let a member change only `status`, `claimedByProfileId` and
`completedAt`).

That makes automations precise without guesswork — e.g. only when a parent approved something:

```yaml
conditions:
  - "{{ trigger.event.data.previous_status == 'PENDING_APPROVAL' }}"
  - "{{ trigger.event.data.status == 'DONE' }}"
  - "{{ trigger.event.data.actor.role == 'PARENT' }}"
```

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

## Dashboards
Three ready-to-paste Lovelace dashboards, all set up with a single find/replace of
`FAMILY_adhdtasker` for your family's slug (e.g. `muir_adhdtasker` — the exact ids are in
**Developer Tools → States**). None of them need per-child editing: people, chores and
rewards are generated from the `leaderboard`, `tasks` and `rewards` attributes of one sensor,
so adding or renaming a kid changes nothing.

| File | What | Needs |
|---|---|---|
| [`adhdtasker-hub-dashboard.yaml`](adhdtasker-hub-dashboard.yaml) | **Family Hub** — four views: Today (who's home, what everyone is doing, routines banded morning/afternoon/evening), Chores, Bank (balances + what the points buy), Parent | [Mushroom](https://github.com/piitaya/lovelace-mushroom) + [auto-entities](https://github.com/thomasloven/lovelace-auto-entities); the Bank catalog needs v0.1.5+ |
| [`adhdtasker-family-dashboard-core.yaml`](adhdtasker-family-dashboard-core.yaml) | Same information, plain **core cards** | nothing |
| [`adhdtasker-dashboard.yaml`](adhdtasker-dashboard.yaml) | The original single-view board | nothing |

Presence on the Hub dashboard is optional — a profile is matched to `person.<name>` by slug,
and where no such entity exists that part is simply left off.

> If you edit a template in the Hub dashboard: auto-entities does
> `typeof result === "string" ? result.split(/[\s,]+/) : result`, so a template that *prints*
> its cards gets shredded on whitespace into bogus entities and you get a wall of
> "Configuration error". Build a list in a namespace and emit it once as `{{ ns.c }}` so the
> websocket returns a native list. Use a `|` literal block, never `>-`.

## Notes
- **The API key is full family automation access** — it can add, edit, delete, complete and
  approve tasks (completing/approving awards points). Treat it like an admin password. Revoke
  by regenerating in the web app (Manage → Inbound API); the old key dies instantly — then
  re-enter the new key when HA prompts for reauth.
- Points are awarded server-side on complete/approve; the integration never writes scores.
- Completing with no profile awards 0 points — use the `complete_task`/`approve_task` service
  with a `profile`, or assign/claim the task first, to credit a kid.
- Multiple families: add the integration once per family; services take an optional
  `config_entry_id` and the second family's entities get a `_2` suffix.

## License
[MIT](LICENSE).
