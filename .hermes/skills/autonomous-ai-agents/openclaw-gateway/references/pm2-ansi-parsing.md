# PM2 Status Parsing: ANSI Color Trap

## Problem

`pm2 show <name>` output includes ANSI escape codes for terminal coloring:

```
│ status            │ ←[32m←[1monline←[22m←[39m                                   │
```

When captured via `subprocess` in Python, these raw codes **are not stripped**.
A naive `.strip()` on `parts[2]` returns `'\x1b[32m\x1b[1monline\x1b[22m\x1b[39m'`,
which does NOT match `'online'`.

Result: all services appear `status=unknown`, triggering false-positive restarts.

## Fix

Strip ANSI escape codes with regex before parsing:

```python
import re
clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_output)
```

Then parse the cleaned output for status keywords.

## Safer Pattern: Use PM2 JSON Output

Alternatively, avoid ANSI entirely by using PM2's machine-readable format:

```bash
pm2 jlist           # full JSON of all processes
pm2 describe <id>   # JSON for one process
```

But `pm2 show` is the most human-friendly debugging command — so the ANSI-strip
approach is better for scripts that also log to console for debugging.
