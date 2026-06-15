# Cloudflare DNS Cleanup Guide

## Process

1. List all DNS records
2. Verify each by visiting
3. Mark: keep / delete / confirm
4. Get user confirmation for deletions
5. Execute deletions
6. Verify remaining records work

## Common Abandoned Record Types

| Type | How to Identify | Action |
|------|----------------|--------|
| Test address | Points to 192.0.2.1, 198.51.100.x | Delete |
| External redirect | Jumps to external domain | Delete (or verify if intentional) |
| Unreachable | Timeout, refuse, 404/500 | Confirm with user |
| Memory fuzzy | User unsure, needs verification | Verify then decide |

## Cautions

- Confirm before deleting critical endpoints (callback, webhook)
- List all deletions for user confirmation before executing
- Verify remaining domains work after cleanup