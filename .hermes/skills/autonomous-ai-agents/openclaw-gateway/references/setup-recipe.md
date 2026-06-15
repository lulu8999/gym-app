# OpenClaw Gateway Setup Recipe (Session Proven)

## Final Working PM2 Setup

```bash
pm2 start bash --name "openclaw-gateway" -- \
  -c "openclaw gateway run --port 9000 --auth none --allow-unconfigured --bind loopback"
pm2 save
```

## Chrome Installation (OpenCloudOS / no apt)

```bash
# Dependencies
yum install -y wget which

# Download and install
wget -q -O /tmp/chrome.rpm 'https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm'
rpm -ivh --nodeps /tmp/chrome.rpm

# At this point Chrome works headless with --no-sandbox
# Gateway auto-detects it and enables the browser plugin
```

## Debugging Timeline

| Attempt | Command | Result |
|---------|---------|--------|
| 1 | `pm2 start openclaw -- gateway ...` | Process online, no port listening |
| 2 | `openclaw gateway run --port 9000 --auth none` | Fails: "Refusing to bind gateway to lan without auth" |
| 3 | `openclaw gateway run --port 9000 --auth none --bind loopback` | ✅ Works! Port 9000 listening |
| 4 | `pm2 start openclaw -- gateway run ...` | Process online, no port (fork mode incompatible) |
| 5 | `pm2 start bash -- -c "openclaw gateway run ..."` | ✅ PM2 works, port 9000, logs visible |

## Verification

```bash
# Port check
ss -tlnp | grep 9000
# Expected: LISTEN 0 511 127.0.0.1:9000 users:(("openclaw",...))

# Log check
pm2 logs openclaw-gateway --lines 5 --nostream
# Expected: "http server listening (8 plugins: ...; 5.9s)" then "ready"
```
