# Geolocation Sharing via Subdomain Tunnel

Built for collecting city-level locations from multiple users for weather report integration.

## Architecture

```
用户手机浏览器 → https://loc.example.com/?user=UserID
    ↓
Cloudflare tunnel → cloudflared agent → Python HTTP server (localhost:18888)
    ↓
用户点击"分享位置" → 浏览器弹授权 → Geolocation API → POST /submit-location
    ↓
Python server → 存储到 locations.json
```

## Components

### 1. Python HTTP Server (`location_server.py`)

Simple `http.server`-based server that:
- Serves an HTML page with Geolocation API
- Accepts `?user=` query param to identify who's submitting
- Handles POST `/submit-location` with `{name, latitude, longitude, timestamp}`
- Saves to `locations.json` keyed by username
- Optionally reverse-geocodes via Nominatim API for city name

**Key design:** Embed `window.USER` from URL param so users don't need to type anything:
```python
# In do_GET handler:
user = parse_qs(urlparse(self.path).query).get('user', [None])[0]
if user:
    html = html.replace(b'</title>',
        f'</title><script>window.USER="{user}";</script>'.encode())
```

### 2. HTML Page (`share.html`)

Uses `navigator.geolocation.getCurrentPosition()` — the standard browser prompt API. 
- Shows "分享位置" button
- If `window.USER` is set: auto-fills name, hides input field
- On success: POSTs coordinates to `/submit-location`
- On failure: shows user-friendly error messages for each error code

### 3. Storage Format (`locations.json`)

```json
{
  "KuHai": {
    "latitude": 32.0973,
    "longitude": 118.6509,
    "city": "南京",
    "updated_at": "2026-06-03T14:31:57"
  }
}
```

### 4. Subdomain via Cloudflare Tunnel

See `subdomain-tunnel-routing.md` for the tunnel setup steps.

## PM2 Lifecycle

```bash
pm2 start location_server.py --name location-server --interpreter python3 -- 18888
pm2 save
pm2 restart location-server   # after code changes
```

## Pitfalls

- **Geolocation requires HTTPS** — The Geolocation API only works on secure contexts (HTTPS or localhost). Cloudflare proxy + tunnel provides HTTPS automatically.
- **Nominatim rate limiting** — Reverse geocoding via `nominatim.openstreetmap.org` has strict rate limits. Add delays or cache results.
- **Location is approximate** — Browser geolocation is GPS/WiFi dependent. Good enough for city-level weather, not for precise tracking.
- **One-time submission** — This design assumes one submission per user. No update mechanism built in.
- **Name mismatch** — The `user` param in the URL must match the WeCom userid. Verify before creating links.
