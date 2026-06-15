---
name: hermes-admin-panel
title: Hermes Admin Web Panel
description: "Build a lightweight Flask admin panel that reads Hermes SQLite state.db for user management and session/chat history viewing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [admin, dashboard, flask, sqlite, state.db, users, sessions]
    related_skills: [subagent-driven-development, hermes-agent]
---

# Hermes Admin Web Panel

Build a lightweight web admin panel for Hermes Agent that provides user management and chat history viewing by reading directly from the Hermes SQLite database (`state.db`).

No additional API calls needed — zero token cost for displaying data.

## Architecture

```
┌─────────────┐     cloudflared      ┌──────────────┐
│  Browser     │ ──────────────────→  │  Flask App    │
│  admin.lulu  │    port 9802         │  (localhost)  │
│  .game.fun   │                      │               │
└─────────────┘                      └──────┬────────┘
                                            │
                                    ┌───────▼────────┐
                                    │  state.db       │
                                    │  (SQLite)       │
                                    └────────────────┘
```

## Database Schema (state.db)

Hermes stores all session data in `~/.hermes/state.db` with two key tables:

### sessions table

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,            -- session ID (e.g. "20260603_120603_fdbf7318")
    source TEXT NOT NULL,           -- platform: "weixin", "cli", "cron", "discord", etc.
    user_id TEXT,                   -- platform user ID (e.g. WeChat ID)
    model TEXT,                     -- model used
    title TEXT,                     -- auto-generated session title
    started_at REAL,                -- Unix timestamp
    ended_at REAL,                  -- Unix timestamp
    message_count INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_cost_usd REAL,
    ...
)
```

### messages table

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,             -- "user", "assistant", "tool"
    content TEXT,                   -- message text content
    tool_calls TEXT,                -- JSON of tool calls (if assistant)
    tool_name TEXT,                 -- tool name (if tool role)
    timestamp REAL,                 -- Unix timestamp
    token_count INTEGER,
    ...
)
```

### Key queries

```python
# Recent sessions
SELECT id, title, source, user_id, message_count, started_at,
       input_tokens, output_tokens, estimated_cost_usd
FROM sessions
WHERE message_count > 0
ORDER BY started_at DESC
LIMIT 100

# Messages for a session
SELECT id, role, content, tool_calls, tool_name, timestamp, token_count
FROM messages
WHERE session_id = ?
ORDER BY id ASC
```

## Implementation pattern

### 1. Flask app structure

```
/root/admin/
├── app.py                 # Flask application
├── .admin_password        # Auto-generated login password
├── templates/
│   ├── login.html         # Dark-themed login page
│   ├── index.html         # Dashboard with user list + stats
│   ├── user.html          # User detail: profile + memory + sessions
│   └── session.html       # Session chat history
└── static/                # (optional) CSS/JS assets
```

### 2. User data source (extended: access.yaml auto-discovery)

The `/root/users-data/` directory stores per-user data in a library-style structure. However, the admin panel also reads from `~/.hermes/access.yaml` to auto-discover users that don't have a directory:

```python
def get_library_users():
    \"\"\"Merge users from users-data/ AND access.yaml\"\"\"
    users = []
    seen_names = set()

    # 1. From users-data directories
    for name in sorted(os.listdir(USERS_DIR)):
        ...  # read profile.json as before

    # 2. From access.yaml — users without a directory
    import yaml
    with open(ACCESS_PATH) as f:
        access_data = yaml.safe_load(f) or {}
    for u in access_data.get('users', []):
        name = u.get('name', '')
        if name.lower() in seen_names:
            continue
        dir_name = f"{name}_{u['id']}"
        users.append({
            'name': dir_name,
            'dir': None,          # no physical directory
            'channel_id': u['id'],
            'channel_type': u.get('platform', 'wecom'),
            'role': u.get('role', ''),
            'from_access': True,  # flag for template
        })

    return users
```

For virtual users, `get_user_profile(name)` falls back to access.yaml by extracting the user ID from the directory name (format `{name}_{userId}`) and looking it up:

```python
def get_user_profile(name):
    # 1. Try users-data directory
    # 2. Fallback: extract userId from name suffix, look up in access.yaml
    suffix = name.split('_')[-1]
    for u in access_data.get('users', []):
        if u.get('id', '') == suffix:
            return {'channel_id': u['id'], 'channel_type': ...,
                    'virtual': True}
    return {}
```

**Key design decision:** Virtual users have `dir: None` and are NOT created in `users-data/`. Their profile info is synthesized from access.yaml on each request. This means adding a new user to access.yaml makes them immediately visible on the admin panel without any filesystem setup.

The index template can show `from_access` and `role` tags:

```html
{% if u.role == 'trusted' %}<span class="tag tag-other">可信</span>{% endif %}
{% if u.role == 'admin' %}<span class="tag tag-admin">管理</span>{% endif %}
{% if u.from_access %}<span class="tag tag-wecom">企微</span>{% endif %}
```

And sent-message counts on the index:

```python
# in index() route
sent_counts = {}
for u in users:
    sent_counts[u['name']] = len(get_sent_messages_for_user(u['name']))
return render_template('index.html', sent_counts=sent_counts)
```

```html
{% set msg_count = sent_counts.get(u.name, 0) %}
{% if msg_count > 0 %}· 已发 {{ msg_count }} 条消息{% endif %}
```
/root/users-data/
├── Lulu_LuHaiTian/        # User group (shared space)
│   ├── profile.json
│   ├── portfolio.json
│   ├── memory.md
│   └── prediction_log.json
├── SomeUser/              # Each user gets their own directory
│   ├── profile.json
│   ├── memory.md
│   └── ...
└── AnotherUser/
    └── ...
```

Each user's `profile.json` may contain a `channel_id` field used to match their Hermes sessions.

### 3. Session-user matching (access.yaml method)

Match sessions to users by reading `~/.hermes/access.yaml` for exact user_id/role mappings, NOT guessing via fuzzy string matching on profile.json.

**Key insight:** The old fuzzy approach (contained-in, reverse-contained-in, platform fallback) caused sessions to appear under wrong users. The correct approach is:

```python
import yaml

def _load_access_ids(user_name):
    \"\"\"从 access.yaml 读取 user_id 列表和平台\"\"\"
    access_path = os.path.expanduser('~/.hermes/access.yaml')
    if not os.path.exists(access_path):
        return []
    with open(access_path, encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    known = []
    for u in data.get('users', []):
        if u.get('name', '').lower() == user_name.lower():
            known.append((u['id'], u.get('platform', '')))
    return known

# In match loop:
known_ids = _load_access_ids(user_name)
for row in sessions_query:
    sid = (row['user_id'] or '').lower().strip()
    src = (row['source'] or '').lower().strip()
    for known_id, known_platform in known_ids:
        if known_id.lower() == sid and (not known_platform or known_platform == src):
            match = True
            break
```

**⚠️ CRITICAL:** Profile.json `channel_id` is often a human-readable name (e.g. `LuHaiTian`) that does NOT match the DB's platform user_id (e.g. `o9cq80-...@im.wechat`). Do NOT fall back to fuzzy matching — add the correct platform IDs to `access.yaml` instead.

**When a new user sessions doesn't show up:**
1. Check the DB user_id: `sqlite3 ~/.hermes/state.db "SELECT DISTINCT source, user_id FROM sessions"`  
2. Add the user's ID(s) to `~/.hermes/access.yaml` under `users:` with the correct `id`, `platform`, and `role`
3. The admin panel reads access.yaml live — no restart needed (unless PM2 has stale state)
4. Add auto-refresh to HTML templates: `<meta http-equiv="refresh" content="30">` in `<head>`

**DB inspection command for debugging:**
```bash
sqlite3 ~/.hermes/state.db "SELECT DISTINCT source, user_id FROM sessions"
```

### 4. Login & security

- Simple password auth via cookie
- Password stored in `.admin_password` file
- Auto-generated on first access via `secrets.token_hex(6)`
- 24-hour cookie expiry

```python
def get_admin_password():
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE) as f:
            return f.read().strip()
    pw = secrets.token_hex(6)
    with open(PASSWORD_FILE, 'w') as f:
        f.write(pw)
    return pw
```

### 5. Deployment

Run via PM2 for auto-restart:

```bash
pm2 start /root/admin/app.py --name admin-panel --interpreter python3
```

### 6. Domain routing

Add to cloudflared config (`/root/.cloudflared/config.yml`):

```yaml
ingress:
  - hostname: admin.example.com
    service: http://localhost:9802
  - ... other services ...
  - service: http_status:404
```

Then restart: `sudo systemctl restart cloudflared`

## Pitfalls

- **state.db is a WAL-mode SQLite file** — use `sqlite3` or Python's `sqlite3` module, not file reads
- **user_id format varies by platform** — WeChat IDs look like `o9cq80-...@im.wechat`, CLI sessions have empty user_id, cron sessions have `cron_` prefix
- **Message content can be long** — truncate display content (>500 chars) to avoid bloated page rendering; provide a "show full" toggle or JSON API endpoint for complete message retrieval
- **Session matching is heuristic** — user_id may not always cleanly match profile.channel_id; show "unmatched" sessions separately
- **⚠️ For-loop scope bug in matching** — NEVER put the channel_id/fallback match INSIDE the `for known_id in known_ids:` loop. When `known_ids` is empty (user dir name doesn't match access.yaml name), the for-loop body never executes, and the fallback never runs → all users show 0 sessions. Always place fallbacks OUTSIDE with `if not match and ...`:
  ```python
  for known_id, known_platform in known_ids:
      if known_id.lower() == sid and ...:
          match = True; break
  # channel_id fallback MUST be outside the loop
  if not match and channel_id and channel_id == sid:
      match = True
  ```
- **key for-loop bug debug:** if a user has sessions in the DB but the panel shows 0, check if `get_library_users()` matched their name. If `known_ids` is empty, the `channel_id` fallback inside the loop never executes. Run `cd /root/admin && python3 -c \"from app import get_sessions_for_user; print(len(get_sessions_for_user('UserName')))\"` to isolate the issue.
- **profile.json channel_id must match DB user_id, not a human-readable name** — if you set `channel_id: "LuHaiTian"` but the DB has `user_id: "o9cq80-...@im.wechat"`, no sessions match. Always verify the actual user_id in the DB first using `SELECT DISTINCT source, user_id FROM sessions WHERE user_id IS NOT NULL`. Then update the profile or add bidirectional matching rules
- **Updating profile.json requires restarting the admin panel** — PM2 restart needed: `pm2 restart admin-panel`. Profile is read on every request, but only if the file is re-read from disk (Flask doesn't cache profile reads by default, but PM2 may have stale in-memory state)
- **Token stats are estimates** — `estimated_cost_usd` and token counts may be approximations depending on the provider
- **Tool messages contain raw JSON** in `tool_calls` and `content` fields — display them collapsed by default
- **No hot-reload for cloudflared** — must restart the service after config changes
- **Password is plaintext** — stored in a file readable by root only; change the password by editing `.admin_password` directly

### ⚠️ JavaScript API calls need credentials

When adding JavaScript (e.g., kanban.js, dashboard.js) that calls Flask `/api/*` endpoints protected by `@login_required`, you MUST include credentials:

```javascript
// ❌ WRONG - will get 401/302 redirect to login
const res = await fetch('/api/kanban/agents');

// ✅ CORRECT - sends cookies with the request
const res = await fetch('/api/kanban/agents', { credentials: 'include' });
if (res.status === 302 || res.status === 401) {
    window.location.href = '/login?next=/kanban';
    return;
}
```

This applies to all fetch/XHR calls to protected Flask routes. The browser won't send authentication cookies otherwise.

## When to Use

Build this panel when:
- You need a lightweight web UI to view Hermes chat history by user
- You want zero-API-cost data browsing
- You need to manage users and their associated sessions
- You want a simple admin interface behind Cloudflare Tunnel

## Extending with new read-only pages

A recurring task is adding new read-only display pages (e.g. cron execution records, system logs, file browser). Follow this pattern:

### 1. Add helper functions in `app.py`

```python
CRON_OUTPUT_DIR = os.path.join(HERMES_HOME, 'cron', 'output')

def get_cron_job_runs(job_id):
    """Scan a directory for sorted .md output files"""
    job_dir = os.path.join(CRON_OUTPUT_DIR, job_id)
    if not os.path.isdir(job_dir):
        return []
    runs = []
    for fname in sorted(os.listdir(job_dir), reverse=True):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(job_dir, fname)
        stat = os.stat(fpath)
        runs.append({
            'filename': fname,
            'time_label': fname.replace('.md', '').replace('_', ' '),
            'size': stat.st_size,
            'mtime': stat.st_mtime,
        })
    return runs
```

Key points:
- **No DB needed for file-based data** — read from filesystem directly
- **Sort descending** for chronological display (newest first)
- **Path traversal protection**: use `os.path.realpath()` and verify the resolved path starts with the expected base directory when serving user-facing file content
- **Graceful degradation**: return `[]` or `None` on missing files/dirs, never crash

### 2. Add routes

```python
@app.route('/cron')
@login_required
def cron_list():
    jobs = get_cron_jobs()  # reads jobs.json
    return render_template('cron.html', jobs=jobs)

@app.route('/cron/<job_id>')
@login_required
def cron_job_detail(job_id):
    # find job in list, get its runs
    return render_template('cron_job.html', job=job, runs=runs)

@app.route('/cron/<job_id>/<filename>')
@login_required
def cron_job_run_detail(job_id, filename):
    content = get_cron_job_run(job_id, filename)
    if content is None:
        return '记录不存在', 404
    return render_template('cron_run.html', content=content)
```

Always include `@login_required` and handle 404s gracefully.

### 3. Create template (GitHub Dark theme)

Copy existing template styling — consistent design matters more than unique per-page CSS:

```html
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
        background: #0d1117; color: #c9d1d9;
    }
    .header {
        background: #161b22; border-bottom: 1px solid #30363d;
        padding: 16px 24px; display: flex; align-items: center; gap: 16px;
    }
    .header h1 { font-size: 20px; }
    .header .back { color: #8b949e; text-decoration: none; }
    .header .back:hover { color: #58a6ff; }
    .container { max-width: 1000px; margin: 0 auto; padding: 24px; }
</style>
```

### 4. Add entry point on index page

```html
<div class="section-title">⏰ 定时任务</div>
<a href="{{ url_for('cron_list') }}" class="user-link">
    <div class="user-card" style="margin-bottom:20px;">
        <div class="name">{{ stats.cron_total }} 个任务</div>
        <div class="info">点击查看执行记录 →</div>
    </div>
</a>
```

### 5. Restart

```bash
pm2 restart admin-panel
# Verify
curl -s -b "admin_token=<password>" http://127.0.0.1:9802/cron | grep "任务"
```

See `references/cron-output-page.md` for a complete implementation example.

### Recent-sessions timeline (index page enhancement)

Add a timeline of all recent sessions to the index page so admins see all activity at a glance without drilling into each user:

```python
# In app.py — helper function
def get_recent_sessions(limit=30):
    \"\"\"Get all recent sessions, including unattributed (CLI/cron)\"\"\"
    sessions = []
    conn = get_db()
    cur = conn.execute(\"""
        SELECT id, title, source, user_id, message_count,
               started_at, input_tokens, output_tokens
        FROM sessions WHERE message_count > 0
        ORDER BY started_at DESC LIMIT ?
    \""", (limit,))
    for row in cur.fetchall():
        row = dict(row)
        uid = (row['user_id'] or '').strip()
        row['has_user'] = bool(uid)
        src = (row['source'] or '').lower()
        row['category'] = 'cron' if src == 'cron' else 'cli' if src == 'cli' else 'user' if uid else 'other'
        sessions.append(row)
    conn.close()
    return sessions

# In index() — pass to template
recent = get_recent_sessions(30)
return render_template('index.html', users=users, stats=stats, recent_sessions=recent)
```

In the template, render a colored timeline with dots (blue=user, red=cron, green=cli, gray=other). Include auto-refresh via `<meta http-equiv="refresh" content="30">`.

## Related

- `subagent-driven-development` — for building the admin panel code via delegation
- `hermes-agent` — for Hermes configuration and provider setup
- `claude-code-plan-execute` — follow this workflow for complex admin panel changes

## 企业微信消息日志集成

See `references/wecom-message-log.md` for integrating sent-message history into the admin panel.

Key files created:
- `~/.hermes/wecom_message_log.jsonl` — append-only JSONL log
- `~/.hermes/scripts/wecom_log.py` — Python query/record module
- `~/.hermes/scripts/backfill_wecom_log.py` — historical data extraction from cron outputs and session DB

Use case: 企业微信用户的单向推送消息（cron 定时任务、手动发送的欢迎词等）不存储在 Hermes session DB 中。通过旁路 JSONL 日志 + admin panel 读取，在用户详情页显示历史发送记录。
