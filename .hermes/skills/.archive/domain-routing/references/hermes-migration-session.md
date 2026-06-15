# Session: OpenClaw → Hermes Migration (2026-06-03)

## Initial situation
- `lulugame.fun` was pointing to `localhost:9800` (OpeniLink Hub / oih service)
- Caddy's Caddyfile had `lulugame.fun { reverse_proxy 127.0.0.1:18789 }` but this was irrelevant
- Reason: **cloudflared tunnel** was active, bypassing Caddy entirely

## Root cause
cloudflared tunnel ingress config at `/root/.cloudflared/config.yml`:
```yaml
ingress:
  - hostname: lulugame.fun
    service: http://localhost:9800   # ← This was serving the wrong content
```

## Fix applied
1. Changed tunnel ingress: `lulugame.fun` → `http://localhost:9119`
2. Removed obsolete `term.lulugame.fun` entry
3. Modified Caddyfile to bind port 80 explicitly to avoid HTTPS redirect conflicts with Cloudflare Flexible SSL:
   ```
   lulugame.fun:80 {
       reverse_proxy 127.0.0.1:9119
   }
   ```
4. Restarted: `sudo systemctl restart cloudflared` then `sudo systemctl restart caddy`

## Verification
- Local: `curl -s -H "Host: lulugame.fun" http://localhost:80/ | head -10` → Hermes Dashboard HTML
- Cloudflare: `curl -s https://lulugame.fun/ | head -10` → Hermes Dashboard HTML
