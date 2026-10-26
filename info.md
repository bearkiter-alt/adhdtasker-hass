# ADHDTasker

Native Home Assistant integration for the [ADHDTasker](https://adhdtasker.com) family
chore-and-rewards app.

- **To-do entity** for the board — add / complete / rename / delete tasks.
- **Sensors** — open & pending counts, per-kid points & balance, last event.
- **Services** — add_task, add_interrupt, claim_task, complete_task, approve_task, ping.
- **Webhook push** + `adhdtasker_event` bus event for automations.

Set-up is one step: paste the API key from the web app (**Manage → Inbound API**).
Three ready-made dashboards are included, incl. a four-view **Family Hub** (who's home, routines by time of day, chores, and a Bank showing who can afford what).
