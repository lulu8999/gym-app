# Location Sharing Service — Design Pattern

Build a browser-based geolocation sharing page that lets users share their city location for weather/notification services.

## Architecture

```
User's Phone Browser → loc.example.com → cloudflared Tunnel
    ↓                                              ↓
HTML Page (Geolocation API)              Python HTTP Server(:18888)
    ↓                                              ↓
User clicks "Share" → Browser asks            POST /submit-location
permission → gets coords                    → Nominatim reverse geocode
                                           → saves to locations.json
```

## Components

### 1. HTML Page (`templates/share.html`)

- Uses `navigator.geolocation.getCurrentPosition()` 
- Shows a button → requests permission → sends coords via POST
- Styled as a clean mobile card
- Handles all error states (denied, unavailable, timeout)

### 2. Python Server (`location_server.py`)

```python
# GET  /              → serves HTML page
# POST /submit-location → receives {latitude, longitude, timestamp}
#                        → reverse geocode via Nominatim
#                        → save to locations.json
#                        → return {status, city, coords}
```

### 3. Deployment

- Run under PM2: `pm2 start location_server.py --interpreter python3 -- <port>`
- Default port: 9803 (实际部署用 9803，旧端口 18888 已废弃）
- Expose via cloudflared tunnel subdomain (e.g., `loc.lulugame.fun`)

## Tunnel Config

Add to `~/.cloudflared/config.yml`:
```yaml
ingress:
  - hostname: loc.lulugame.fun
    service: http://localhost:9803
```

Then restart tunnel and add DNS:
```bash
cloudflared tunnel route dns <tunnel-name> loc.example.com
sudo systemctl restart cloudflared
```

## Reverse Geocoding

Uses OpenStreetMap Nominatim (free, no API key):
```
GET https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=10&accept-language=zh
```

Response parsing priority: `city` > `county` > `town` > `state`

**Rate limit:** 1 request/second (proper etiquette — this is a free service).

## File Structure

```
~/.hermes/scripts/location_server/
├── location_server.py     # HTTP server
├── templates/
│   └── share.html         # Geolocation page
└── locations.json         # Saved locations (auto-created)
```

## Privacy Considerations

1. Browser's Geolocation API always shows a permission prompt — user must explicitly grant access
2. Only city-level location is stored (reverse geocoded)
3. Data stays on the server, not shared externally
4. Inform users what the location is used for (weather/service personalization)

## Pitfalls

- HTTPS required for Geolocation API in most browsers. Cloudflare Tunnel handles this automatically.
- iOS Safari may require user interaction (touch) to trigger geolocation
- **Nominatim requires a `User-Agent` header** or it will return 403/429. Always set one:
  ```python
  req = urllib.request.Request(url, headers={'User-Agent': 'AppName/1.0'})
  ```
- **Nominatim rate limit is ~1 req/sec** — if the server is processing multiple requests quickly, expect timeouts. Solution: cache results or batch with delays between requests.
- If the page is opened in WeChat's built-in browser, the WeChat X5 rendering engine may not support Geolocation. Advise user to open in system browser instead.
- **Geolocation in HTTP only works on `localhost`** — need HTTPS for production. Cloudflare Tunnel provides free HTTPS automatically.
