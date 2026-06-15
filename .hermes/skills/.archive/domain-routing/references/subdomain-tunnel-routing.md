# Serving a Subdomain via cloudflared Tunnel

Example used in this session: exposing a location-sharing page at `loc.lulugame.fun`

## Steps

1. **Edit tunnel config** (`~/.cloudflared/config.yml`):
   ```yaml
   ingress:
     - hostname: loc.example.com
       service: http://localhost:18888    # ← new subdomain
     - hostname: example.com
       service: http://localhost:9119
     - service: http_status:404
   ```

2. **Create DNS record automatically** (no dashboard needed):
   ```bash
   cloudflared tunnel route dns <tunnel-name> loc.example.com
   ```
   This creates a CNAME record `loc.example.com.cdn.cloudflare.net` automatically.

3. **Restart tunnel**:
   ```bash
   sudo systemctl restart cloudflared
   ```

4. **Start backend service** (if not already running):
   ```bash
   pm2 start server.py --name location-server -- <port>
   pm2 save
   ```

## Verification
```bash
curl -s https://loc.example.com/ | head -5
# Should see your service's HTML content
```

## Pitfalls

- Adding the ingress rule alone is NOT enough — you must also create the DNS record. Without it, Cloudflare won't know where to route traffic.
- `cloudflared tunnel route dns` does this automatically. Manual DNS record creation through the dashboard also works but is error-prone.
- Order matters in the ingress array: specific subdomains above general/catch-all entries. First match wins.
- Caddy also listening on ports 80/443 doesn't conflict — the tunnel takes priority for domains listed in its ingress rules, and passes everything else through to Caddy.
