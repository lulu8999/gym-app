# Session Matching Strategy — Debug Reference

## The Problem

Admin panel users show "0 sessions" even though the Hermes `state.db` has hundreds of messages. This happens when the session matching logic cannot link a `profile.json` entry or an `access.yaml` entry to a database row.

## Root Cause

The sessions table's `user_id` column carries a **platform-native identifier** (e.g. WeChat OpenID `o9cq80-...@im.wechat`), while the admin panel tries to match by directory name (e.g. `Lulu_LuHaiTian`) or a human-readable channel_id.

## Database Reality Check

Run this to see what Hermes actually stores:

```bash
sqlite3 ~/.hermes/state.db "
  SELECT DISTINCT source, user_id, COUNT(*) as session_count
  FROM sessions
  WHERE message_count > 0
  GROUP BY source, user_id
  ORDER BY session_count DESC
"
```

Expected output patterns:

```
weixin|o9cq80-Ct2fnApV5l3YGq1e2gWLQ@im.wechat|3
weixin||2                  # web panel — empty user_id
cli||9                     # CLI — always empty user_id
cron||5                    # cron — always empty user_id
```

## The Access.yaml Approach (Current)

The admin panel now uses `access.yaml` as the primary matching source, not profile.json.

### How matching works

In `get_sessions_for_user(user_name)`:

```python
# 1. Load profile for channel_id fallback
profile = get_user_profile(user_name)
channel_id = profile.get('channel_id', '').lower()

# 2. Load known_ids from access.yaml (match by name)
import yaml
known_ids = []
if os.path.exists(access_path):
    with open(access_path) as f:
        access_data = yaml.safe_load(f) or {}
    for u in access_data.get('users', []):
        if u.get('name', '').lower() == user_name.lower():
            known_ids.append((u['id'], u.get('platform', '')))

# 3. Per-session match logic
for row in sessions_query:
    sid = (row['user_id'] or '').lower().strip()
    src = (row['source'] or '').lower().strip()

    match = False
    # 先匹配 access.yaml
    for known_id, known_platform in known_ids:
        if known_id.lower() == sid and (not known_platform or known_platform == src):
            match = True
            break

    # 再尝试 channel_id 兜底
    if not match and channel_id and channel_id == sid:
        match = True

    if not match:
        continue
    # ... append session
```

### ⚠️ CRITICAL BUG: For-loop scope hiding fallback

A real bug found in production: the channel_id fallback was written INSIDE the `for known_id, known_platform in known_ids:` loop:

```python
# BUG: fallback inside the for loop
for known_id, known_platform in known_ids:
    if known_id.lower() == sid:
        match = True
        break
    if channel_id and channel_id == sid:  # ← NEVER reached when known_ids is empty!
        match = True
        break
```

When the user's directory name (e.g. `Lulu_LuHaiTian`) doesn't match the `name` field in `access.yaml` (e.g. `"Lulu"`), `known_ids` is empty, the for-loop iterates 0 times, and the channel_id fallback NEVER executes — resulting in 0 sessions for everyone.

**Fix:** Always place fallback logic OUTSIDE the loop, with an explicit guard:

```python
if not match and channel_id and channel_id == sid:
    match = True
```

### Why profile.json channel_id alone is not enough

The `channel_id` in profile.json may be set correctly to the WeChat ID, but the name-based lookup in access.yaml may fail first. The fallback MUST be unconditionally reachable.

A secondary issue: if the access.yaml entry names don't use directory names (e.g. `name: "Lulu"` vs dir `Lulu_LuHaiTian`), the access.yaml loop produces no matches for anyone except exact matches.

## Matching Strategy Summary

| # | Strategy | When it works | Why it fails |
|---|----------|---------------|-------------|
| 1 | access.yaml `id` == `user_id` | User ID in access.yaml matches DB exactly | Name in access.yaml doesn't match directory name → empty loop → no match |
| 2 | channel_id == user_id (fallback) | profile.json has correct DB user_id | Fallback inside for-loop → never reaches |
| 3 | channel_id == user_id (fixed, outside loop) | ✅ Reliable | Works even when access.yaml name doesn't match |

## Edge Cases

- **CLI/cron sessions** have empty `user_id` — they can never match any profile. Show them in a separate "System" category on the dashboard index.
- **Web panel sessions** (`source=weixin`, `user_id=''`) — also unmatched by user_id. These are admin panel interactions by the user, not regular WeChat chats.
- **Multiple profiles map to same sessions** — If access.yaml has multiple entries with different names pointing to the same ID, that's fine and intentional (aliases).
- **Platform migration** — If switching platforms, old sessions have one user_id format and new sessions have another. Add both IDs to access.yaml under the same user.
