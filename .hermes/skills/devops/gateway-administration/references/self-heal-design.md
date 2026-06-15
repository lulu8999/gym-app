# Self-Heal Script Design

## Architecture

`/root/scripts/hermes_self_heal.py` — monitors PM2 services, auto-recovers failures.

### Three modes

| Mode | Command | Behavior |
|------|---------|----------|
| `backup` | `python3 hermes_self_heal.py backup` | Creates tar.gz of config.yaml, .env, access.yaml, plugins/, skills/, cron/, scripts/ |
| `check` | `python3 hermes_self_heal.py check` | Backup → health check → auto-recover → silent if ok |
| `restore` | `python3 hermes_self_heal.py restore` | Restore from latest backup |

### Check flow

```
check()
├── do_backup()            # Rotates last 5, creates timestamped tar.gz
├── check_all()
│   ├── pm2 running?
│   ├── each service: pm2 status + port listening?
│   └── config.yaml exists?
├── if no issues → silent exit (no output)
├── if issues → fix_issues()
│   ├── Read old state from .self_heal_last_state.json
│   ├── Write current state (for next check's dedup)
│   └── For each issue:
│       ├── Process online but port not ready? → skip (transient)
│       ├── Same issue as previous check? → skip (persistent, not transient)
│       ├── In cooldown (RESTART_COOLDOWN=120s)? → skip
│       ├── pm2 restart/gateway → record _last_restart timestamp
│       └── Verify port after restart
└── if all fixed → silent
└── if unfixable → print report (cron will deliver to admin)
```

### Key design decisions

1. **Silence on success** — no output when all services healthy or auto-recovered. Only output when unfixable.
2. **Cooldown prevents loops** — `RESTART_COOLDOWN=120s` prevents repeated restarts.
3. **State-based dedup** — `.self_heal_last_state.json` stores previous check's issues. If the same problem appears on consecutive checks, it's "persistent" not "transient" — don't make it worse by restarting.
4. **Transient grace** — "process online but port not listening" is normal during startup. Skip, don't restart.
5. **Read then write** — The state file read must happen BEFORE the state file write, otherwise the script compares against its own just-written state (false positive dedup).

## PM2 Status Parsing

`pm2 show <name>` includes ANSI codes. The correct parsing pattern:

```python
import re

def pm2_status(name):
    code, out = run_cmd(["pm2", "show", name])
    if code != 0:
        return "not_found"
    clean = re.sub(r'\x1b\[\d+(;\d+)*[a-zA-Z]', '', out)
    for line in clean.splitlines():
        line = line.strip()
        if line.startswith("│ status") and "│" in line[10:]:
            parts = line.split("│")
            if len(parts) >= 3:
                status = parts[2].strip()
                if status in ("online", "stopped", "errored"):
                    return status
    return "unknown"
```

### Safer alternative: PM2 JSON

```bash
pm2 jlist           # all processes as JSON
pm2 describe <id>   # single process as JSON
```

But `pm2 show` is better for debugging — so the ANSI-strip approach is preferred
for scripts that also log to console.

## Config

| Setting | Location | Value |
|---------|----------|-------|
| Backup dir | `BACKUP_DIR` in script | `~/.hermes/backups/` |
| Max backups | `MAX_BACKUPS` | 5 |
| Cooldown | `RESTART_COOLDOWN` | 120 seconds |
| State file | `_STATUS_FILE` | `~/.hermes/.self_heal_last_state.json` |
