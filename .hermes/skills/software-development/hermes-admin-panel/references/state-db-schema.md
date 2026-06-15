# Hermes state.db Schema Reference

Location: `~/.hermes/state.db`
Format: SQLite (WAL mode)

## Tables

### sessions

Stores one row per Hermes conversation session.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Session ID, e.g. `20260603_120603_fdbf7318` |
| source | TEXT | Platform: `weixin`, `cli`, `cron`, `discord`, `telegram`, etc. |
| user_id | TEXT | Platform user ID (WeChat ID, Discord ID, etc.) |
| model | TEXT | Model used (e.g. `deepseek-v4-flash`) |
| model_config | TEXT | JSON of model config |
| system_prompt | TEXT | System prompt used |
| parent_session_id | TEXT | Parent session (for forked/continued sessions) |
| started_at | REAL | Unix timestamp |
| ended_at | REAL | Unix timestamp |
| end_reason | TEXT | Why session ended |
| message_count | INTEGER | Total messages |
| tool_call_count | INTEGER | Tool calls made |
| input_tokens | INTEGER | Total input tokens |
| output_tokens | INTEGER | Total output tokens |
| cache_read_tokens | INTEGER | Cache read tokens |
| cache_write_tokens | INTEGER | Cache write tokens |
| reasoning_tokens | INTEGER | Reasoning tokens (thinking models) |
| cwd | TEXT | Working directory |
| billing_provider | TEXT | Provider used |
| billing_base_url | TEXT | API endpoint used |
| estimated_cost_usd | REAL | Estimated cost |
| actual_cost_usd | REAL | Actual cost (if available) |
| title | TEXT | Auto-generated session title |
| api_call_count | INTEGER | API calls made |
| handoff_state | TEXT | Handoff state for cross-platform |
| handoff_platform | TEXT | Platform handed off to |
| archived | INTEGER | 0 or 1 |

### messages

Stores individual messages within sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK AUTO | Message ID |
| session_id | TEXT FK→sessions(id) | Parent session |
| role | TEXT | `user`, `assistant`, `tool` |
| content | TEXT | Message text content (can be long) |
| tool_call_id | TEXT | Tool call ID (for tool responses) |
| tool_calls | TEXT | JSON array of tool calls |
| tool_name | TEXT | Tool name (for tool role messages) |
| timestamp | REAL | Unix timestamp |
| token_count | INTEGER | Token count for this message |
| finish_reason | TEXT | Why generation stopped |
| reasoning | TEXT | Reasoning/thinking content |
| reasoning_content | TEXT | Displayed reasoning |
| platform_message_id | TEXT | Platform-specific message ID |
| observed | INTEGER | 0 or 1 |
| active | INTEGER | 1 = active, 0 = compacted/removed |

### schemaversion, state_meta, compression_locks

Internal Hermes tables for version tracking, metadata, and context compression locks.

### FTS5 virtual tables

`messages_fts` and `messages_fts_trigram` — full-text search indexes over message content. Used by the `session_search` tool.

## Sample Queries

```sql
-- Recent active sessions
SELECT id, title, source, user_id, message_count,
       datetime(started_at, 'unixepoch', '+8 hours') as time_cst,
       input_tokens, output_tokens, estimated_cost_usd
FROM sessions
WHERE message_count > 0
ORDER BY started_at DESC
LIMIT 20;

-- Messages for a specific session (last 50)
SELECT id, role, substr(content, 1, 200) as content_preview,
       datetime(timestamp, 'unixepoch', '+8 hours') as time_cst,
       token_count, tool_name
FROM messages
WHERE session_id = 'SESSION_ID_HERE'
ORDER BY id ASC;

-- Token usage by platform
SELECT source, COUNT(*) as sessions,
       SUM(input_tokens) as total_input,
       SUM(output_tokens) as total_output,
       SUM(estimated_cost_usd) as total_cost
FROM sessions
GROUP BY source
ORDER BY total_cost DESC;

-- Sessions for a specific user (by user_id)
SELECT id, title, message_count, started_at
FROM sessions
WHERE user_id LIKE '%USER_ID_PART%'
ORDER BY started_at DESC;
```

## Notes

- timestamps are Unix epoch in seconds (not milliseconds)
- Add 8 hours for China Standard Time (CST / Asia/Beijing) display
- content field can be very large (entire tool results) — always truncate for display
- tool_calls is a JSON string; parse with `json.loads()` in Python
- user_id varies by platform: WeChat uses email-like IDs, CLI is empty, cron has `cron_` prefix
