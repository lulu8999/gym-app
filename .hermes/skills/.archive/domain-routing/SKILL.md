---
name: domain-routing
category: devops
description: Troubleshoot and configure domain routing behind Cloudflare — Caddy, Nginx, cloudflared tunnel, and DNS resolution.
---

# Domain Routing Troubleshooting

Diagnose why a domain isn't serving the expected content when behind Cloudflare. Covers Caddy, cloudflared tunnel, Nginx, and DNS resolution.

## Quick Checks (in order)

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

## Cloudflare Tunnel (cloudflared)

Cloudflare Tunnel creates a direct connection from Cloudflare's edge to the local cloudflared agent, **completely bypassing Caddy/Nginx**.

**Config file:** `/root/.cloudflared/config.yml`
```yaml
tunnel: <name>
credentials-file: /root/.cloudflared/<uuid>.json

ingress:
  - hostname: example.com
    service: http://localhost:<port>  # ← This is what actually serves the domain
  - service: http_status:404
```

**Commands:**
- View config: `cat /root/.cloudflared/config.yml`
- Restart tunnel: `sudo systemctl restart cloudflared`
- Check tunnel status: `systemctl status cloudflared`

### Adding a Subdomain to the Tunnel

To expose an additional subdomain through the tunnel:

1. **Add ingress rule** — Edit `~/.cloudflared/config.yml`:
   ```yaml
   ingress:
     - hostname: sub.example.com
       service: http://localhost:<new-port>
     - hostname: example.com
       service: http://localhost:<existing-port>
     - service: http_status:404
   ```
   Order matters — tunnels match the FIRST entry, so put specific subdomains above catch-all/general entries.

2. **Create DNS record automatically** (requires tunnel API access):
   ```bash
   cloudflared tunnel route dns <tunnel-name> sub.example.com
   ```
   This creates a CNAME record in Cloudflare DNS pointing to the tunnel endpoint.

3. **Restart tunnel**:
   ```bash
   sudo systemctl restart cloudflared
   ```

**Pitfall:** DNS is managed by Cloudflare. If you add an ingress rule without creating the DNS record, the domain won't resolve. Use `cloudflared tunnel route dns` instead of manually adding DNS records through the dashboard to avoid misconfiguration.

**Pitfall:** If cloudflared tunnel is active for a domain, changing Caddy/Nginx config alone has NO EFFECT — the tunnel bypasses them entirely. You MUST change the tunnel's ingress rule.

## Caddy + Cloudflare

### The HTTPS Redirect Problem

Caddy v2 **automatically** redirects HTTP → HTTPS by default. When Cloudflare is in **Flexible SSL mode** (connects to origin via HTTP), this creates a redirect loop or causes Cloudflare to return unexpected content.

**Solution:** Explicitly bind to port 80 to disable the automatic HTTPS redirect:
```
example.com:80 {
    reverse_proxy localhost:<port>
}
```

Without `:80`, Caddy listens on both 80 and 443, with 80 → 308 redirect to 443.

### Verify Caddy config
```bash
cat /etc/caddy/Caddyfile
sudo systemctl restart caddy
# Or: sudo caddy reload --config /etc/caddy/Caddyfile
```

**Logs:** `journalctl -u caddy --no-pager -n 50`

### Caddy + cloudflared coexistence
When both Caddy AND cloudflared tunnel are running, they compete for the same ports (80/443). The tunnel takes priority for domains listed in its ingress rules. Caddy serves everything else.

## Diagnostic Flowchart

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

## Pitfalls

- **Forgetting cloudflared tunnel exists** — The most common mistake. Always check `~/.cloudflared/config.yml` before modifying Caddy/Nginx.
- **Caddy auto-HTTPS** — Caddy silently adds HTTPS redirect. Explicit `:80` port binding is the fix when behind Cloudflare Flexible SSL.
- **Multiple ingress rules** — Cloudflare Tunnel matches the FIRST matching hostname. Order matters in the ingress array.
- **Tunnel restart required** — Editing the config file alone does NOTHING. Must restart: `sudo systemctl restart cloudflared`.
- **Caddy restart also needed** — After modifying Caddyfile: `sudo systemctl restart caddy`.
