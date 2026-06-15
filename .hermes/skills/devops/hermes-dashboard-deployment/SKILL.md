---
name: hermes-dashboard-deployment
description: "Deploy Hermes Agent's Web Dashboard behind a reverse proxy (Caddy, Nginx) with a custom domain."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, dashboard, reverse-proxy, caddy, nginx, deployment, domain, cloudflare]
    related_skills: [hermes-agent]
---

# Hermes Dashboard Deployment

Expose Hermes Agent's Web Dashboard (`hermes dashboard`) to the internet via a custom domain and reverse proxy. This skill covers replacing an existing assistant service (e.g. OpenClaw) with Hermes Dashboard, or setting it up from scratch.

## When to Use

- You want to access Hermes from a browser (desktop or mobile)
- You have a domain pointing to the VPS/server where Hermes runs
- You're replacing an existing AI assistant web interface with Hermes
- You have a reverse proxy (Caddy, Nginx, etc.) already set up

## Prerequisites

- Hermes Agent installed and running
- A domain name pointing to your server's IP (via DNS A/AAAA record or Cloudflare)
- A reverse proxy running on the server (Caddy, Nginx, or similar)

## How It Works

Hermes Dashboard runs on a local port (default: `9119`), bound to `0.0.0.0`. A reverse proxy (Caddy/Nginx) sits in front, handling TLS termination and forwarding requests from your domain to the dashboard's port.

```
Browser ──► domain.com ──► Cloudflare ──► VPS:443 ──► Caddy ──► 127.0.0.1:9119 (Hermes Dashboard)
```

## Step-by-Step

### 1. Check What's Running

First, survey active services and ports:

```bash
ss -tlnp | grep -E '9119|18789|18888'  # Check common Hermes + legacy ports
ps aux | grep hermes | grep -v grep     # Check Hermes processes
```

Hermes Dashboard typically runs as:
```
/root/.hermes/hermes-agent/venv/bin/python /root/.local/bin/hermes dashboard --port 9119 --host 0.0.0.0 --insecure --tui
```

### 2. Identify the Reverse Proxy

Common setups on Linux:

```bash
# Caddy
cat /etc/caddy/Caddyfile

# Nginx
ls /etc/nginx/sites-enabled/
cat /etc/nginx/sites-enabled/*

# Check which is running
ps aux | grep -E 'caddy|nginx' | grep -v grep
```

### 3. Update the Config (Caddy Example)

Replace the old service's port with Hermes Dashboard port (9119):

```caddy
your-domain.com {
    reverse_proxy 127.0.0.1:9119
}
```

**Important:** Remove any unused subdomain/legacy entries to avoid confusion.

### 4. Reload the Reverse Proxy

```bash
# Caddy — try systemctl first, then fallback to direct reload
sudo systemctl reload caddy 2>/dev/null || sudo caddy reload --config /etc/caddy/Caddyfile

# Nginx
sudo nginx -t && sudo systemctl reload nginx
```

### 5. Verify

```bash
# Check dashboard is responding locally
curl -s -o /dev/null -w "%{http_code}" http://localhost:9119/ && echo " Dashboard OK"

# Check reverse proxy is serving the domain (if curl can reach it externally)
curl -s -o /dev/null -w "%{http_code}" https://your-domain.com/ 2>/dev/null || echo "Test in browser instead"
```

### 6. Optional: Configure Dashboard Settings

The Hermes config has a `dashboard` section with useful options:

```yaml
dashboard:
  theme: default          # UI theme
  show_token_analytics: false
  oauth:
    client_id: ''         # OAuth for public deployments
    portal_url: ''
  public_url: ''          # Set to your domain URL if needed
```

Set via CLI:
```bash
hermes config set dashboard.public_url https://your-domain.com
hermes config set dashboard.theme dark    # if available
```

## Cloudflare-Specific Notes

- **DNS only needs to point to your VPS IP** — nothing changes on Cloudflare when you swap the backend service
- If proxied through Cloudflare (orange cloud), TLS is handled by Cloudflare — your reverse proxy just needs to listen on the port Cloudflare sends traffic to
- If using Full (Strict) TLS, ensure your reverse proxy has a valid certificate (Caddy auto-provisions Let's Encrypt certs)
- **SSL/TLS mode matters:** Cloudflare's SSL/TLS encryption setting (in the dashboard) determines whether it connects to your origin via HTTP (Flexible → port 80) or HTTPS (Full/Strict → port 443). Caddy auto-redirects HTTP→HTTPS (308), which can break Flexible mode. If you see unexpected behavior, check this setting.
  
  **Caddy workaround for Flexible SSL:** If Cloudflare is in Flexible mode (HTTP to origin), tell Caddy to listen explicitly on port 80 without the automatic HTTPS redirect:
  ```caddy
  your-domain.com:80 {
      reverse_proxy 127.0.0.1:9119
  }
  ```
  This prevents Caddy from issuing the 308 redirect and serves the Dashboard directly over HTTP to Cloudflare.
- **Check for Cloudflare Workers or Page Rules:** If the domain serves content completely different from what your reverse proxy is proxying, a Cloudflare Worker or Page Rule may be intercepting requests before they reach your server. Log into dash.cloudflare.com → your domain → Workers & Pages / Rules → Page Rules to check.
- **Cloudflare cache may serve stale content:** Even with `cf-cache-status: DYNAMIC`, Workers can inject their own content. Purge Cloudflare cache or add a cache-busting query parameter when testing.

## Troubleshooting

### Domain serves wrong content (different from what's on localhost)

This means something upstream (Cloudflare) is intercepting the request before it reaches your reverse proxy.

**Diagnosis steps:**

1. **Check what the reverse proxy is serving locally:**
   ```bash
   curl -s -H "Host: your-domain.com" http://localhost:80/ | head -10
   # If empty, Caddy may be redirecting HTTP→HTTPS — check with -i:
   curl -s -i -H "Host: your-domain.com" http://localhost:80/ | head -10
   ```

2. **Compare with the dashboard directly:**
   ```bash
   curl -s http://localhost:9119/ | head -10
   # Should show "<title>Hermes Agent - Dashboard</title>"
   ```

3. **Compare with what Cloudflare serves:**
   ```bash
   curl -s https://your-domain.com/ | head -10
   # If this returns different content (e.g. "OpeniLink Hub", "Coming Soon", etc.),
   # a Cloudflare Worker or Page Rule is intercepting the request.
   ```

4. **Check response headers for clues:**
   ```bash
   curl -s -D- https://your-domain.com/ 2>/dev/null | head -20
   ```
   - `server: cloudflare` is normal — Cloudflare always adds this
   - Look for `cf-worker` or custom headers that hint at Workers

5. **Log into Cloudflare dashboard** → your domain → check:
   - **Workers & Pages** — any deployed Workers that match your domain route
   - **Rules → Page Rules** — any rules that redirect or rewrite
   - **SSL/TLS** → check the encryption mode (Flexible/Full/Strict)

6. **Check for Cloudflare Tunnel (`cloudflared`):**
   Cloudflare Tunnel bypasses your reverse proxy entirely — it connects directly from Cloudflare's edge to a local service on your server. If the domain content looks perfect locally but is wrong via the domain, a tunnel is a likely cause.
   
   ```bash
   # Check if cloudflared is running
   ps aux | grep cloudflared | grep -v grep
   
   # View tunnel ingress rules (this is the critical file)
   cat /root/.cloudflared/config.yml
   # Example output:
   # tunnel: wecom
   # ingress:
   #   - hostname: your-domain.com
   #     service: http://localhost:9800    # ← Check this port!
   #   - hostname: sub.your-domain.com
   #     service: http://localhost:18888
   #   - service: http_status:404
   
   # Check cloudflared listening port
   ss -tlnp | grep cloudflared
   ```
   
   **Key insight:** The tunnel ingress takes priority over your Caddy/Nginx config for proxied domains. If `your-domain.com` routes to `localhost:9800` in the tunnel config, changing Caddy is useless — the tunnel wins.
   
   **Fix:** Edit `/root/.cloudflared/config.yml` and change the service URL for your domain to point to Hermes Dashboard:
   ```yaml
   ingress:
     - hostname: your-domain.com
       service: http://localhost:9119    # ← Hermes Dashboard
   ```
   
   **Also audit stale ingress rules:** Check ALL hostname entries in the tunnel config — not just the target domain. Old subdomains (chat, hub, term, admin, etc.) may point to services that no longer run. Remove them to avoid confusion later. Keep only the catch-all `http_status:404` at the end.
   
   Then restart cloudflared:
   ```bash
   sudo systemctl restart cloudflared
   ```
   
   **Check DNS records too:** In the Cloudflare dashboard, the DNS A record for the domain may point to a Cloudflare Tunnel CNAME (e.g. `your-domain.com.cdn.cloudflare.net`) rather than a real IP — this confirms the tunnel is in use.

### Reverse proxy reload doesn't take effect

- `systemctl reload caddy` may fail if the unit doesn't define `ExecReload` — always have `caddy reload --config ...` as fallback
- If reload still doesn't work, do a full restart: `sudo systemctl restart caddy`
- Note: `caddy verify` does NOT exist in Caddy v2.7.x — use `caddy validate` or just check the logs
- **Tunnel vs reverse proxy distinction:** If Cloudflare Tunnel is routing your domain, Caddy changes are irrelevant for that domain. Always check the tunnel config first when using Cloudflare Tunnel.

### Verifying tunnel changes

After editing tunnel config and restarting cloudflared, verify from the server's perspective:

```bash
# Check cloudflared restarted
sudo systemctl status cloudflared --no-pager | grep Active

# Check the local service is reachable (not through tunnel)
curl -s http://localhost:9119/ | head -5
# Should show Hermes Dashboard content

# Check through Cloudflare (actual domain)
curl -s https://your-domain.com/ | head -5
# Should now show the same Hermes Dashboard content

# If tunnel change hasn't taken effect after restart, wait 2-3 seconds
# for the tunnel to re-establish its connection, then retry
```

### Old service still interfering

- Even if the old service process isn't listening on its port anymore, check for leftover config (e.g. `.htpasswd` files in `/etc/caddy/`) that was used by the old service but is now unused

---

## Domain Routing Troubleshooting (General)

> This section consolidates general domain routing guidance from `domain-routing` skill. Use this for any domain routing issue, not just Hermes.

### Quick Checks (in order)

1. **DNS resolution** — `dig +short <domain>` — if it returns Cloudflare IPs (104.x, 172.x), Cloudflare proxy is active (orange cloud). If it returns your server IP, DNS is direct (grey cloud).

2. **What's serving the domain?** — There may be MULTIPLE services intercepting traffic. Check all:
   - `cloudflared tunnel`: check `~/.cloudflared/config.yml` ingress rules
   - `Caddy`: check `/etc/caddy/Caddyfile` (and `Caddyfile.d/`)
   - `Nginx`: check `/etc/nginx/sites-enabled/`
   - Other web servers listening on port 80/443: `ss -tlnp | grep -E ':80 |:443 '`

3. **Local bypass test** — Test directly on the server to isolate Cloudflare:
   ```bash
   curl -s -H "Host: <domain>" http://localhost:80/ | head -10
   ```

### Diagnostic Flowchart

```
User says "domain shows wrong content"
  │
  ├─ dig +short <domain> → Cloudflare IPs?
  │   ├─ YES → Check cloudflared tunnel: `cat ~/.cloudflared/config.yml`
  │   │           └─ Is domain in ingress rules? → Modify tunnel config, restart
  │   └─ NO  → Check Caddy/Nginx config directly
  │
  ├─ curl -H "Host: <domain>" http://localhost:80/ → What content?
  │   ├─ 308 redirect → Caddy auto-HTTPS is active (see solution above)
  │   ├─ 200 (wrong content) → Another service on that port, check routing
  │   └─ 200 (correct content) → Cloudflare is caching or has a Worker/Page Rule
  │
  └─ Check Cloudflare dashboard (if accessible):
      ├─ Workers & Pages section
      └─ Rules → Page Rules section
```
