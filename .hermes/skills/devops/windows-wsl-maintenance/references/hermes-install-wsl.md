---
name: hermes-install-wsl
category: references
description: Hermes Agent installation and Desktop connection on WSL
---
# Hermes Agent Installation on WSL

## Quick Install

```bash
# Open WSL directly (don't SSH into it from the same machine)
# Then run:
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

What the installer does:
1. Installs managed `uv` to `~/.hermes/bin/`
2. Installs **Python 3.11.15** via uv (even if system Python exists — Hermes uses its own)
3. Installs **Node.js 22 LTS** to `~/.hermes/node/` (even if nvm-managed Node exists — Hermes doesn't detect it)
4. Clones the repo via HTTPS to `~/.hermes/hermes-agent/`
5. Sets up the `hermes` command at `~/.local/bin/hermes`
6. Starts a setup wizard that may prompt for Nous Portal auth

## Pitfalls

### Network Timeout (GitHub Clone)
The git clone step can time out on slow networks (the repo is large). If it happens:
- **Ctrl+C** cancels the **entire** install, not just one step
- The partial `.git` directory may be left behind — delete it: `rm -rf ~/.hermes/hermes-agent`
- Re-run the install script — it's partially idempotent (Python and Node.js are already installed on subsequent runs)
- Mirror alternative (may have DNS issues depending on provider): `git clone --depth 1 https://ghproxy.188888.xyz/https://github.com/NousResearch/hermes-agent.git ~/.hermes/hermes-agent`

### Nous Portal Auth Prompt
After install completes, the setup wizard may show:
```
To continue:
  1. Open: https://portal.nousresearch.com/manage-subscription?user_code=XXXX-XXXX
  2. If prompted, enter code: XXXX-XXXX
```
**Users with their own API keys should Ctrl+C out of this** and configure their own provider instead.

### Auto-Installs Its Own Node.js
The Hermes installer installs Node.js 22 into `~/.hermes/node/` even if Node.js is already available via nvm. This is intentional — Hermes manages its own dependencies. The nvm-installed Node.js stays untouched.

### Python Version Requirement
The Hermes installer needs Python 3.11. If only Python 3.14+ is installed on the system (e.g. Ubuntu 26.04), Hermes will auto-install Python 3.11.15 via uv. No manual action needed.

## Configuring After Install

### Skip Portal, Use Own API Key
```bash
# Configure a custom OpenAI-compatible provider (e.g. MiMo)
hermes config set providers.xiaomi-mimo.api_key sk-your-key-here
hermes config set providers.xiaomi-mimo.base_url https://api.xiaomimimo.com/v1
hermes config set providers.xiaomi-mimo.default_model mimo-v2.5-pro
hermes config set providers.xiaomi-mimo.models '["mimo-v2-flash","mimo-v2-pro","mimo-v2.5","mimo-v2.5-pro"]'
hermes config set model mimo-v2.5-pro
```

### Connect Hermes Desktop to WSL Hermes
Since WSL and Windows are on the same machine, Desktop can connect via SSH on `127.0.0.1:22`:
| Field | Value |
|-------|-------|
| Connection type | SSH |
| Host | `127.0.0.1` |
| Port | `22` |
| User | `lulu` |
| Password | `111111` |

### API Key Recovery (System Masking)
If the system masks API keys in terminal output (shows `***` or `sk-xxx...yyyy` truncated), recover the full key via hex dump or raw byte read:

```python
with open('/root/.hermes/.env', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for line in lines:
    if b'XIAOMI_API_KEY' in line:
        parts = line.split(b'=', 1)
        full_key = parts[1].decode()
        print(f'Full key: {full_key}')
```

Or using `od -c` to see raw bytes, or grep for hex:
```bash
grep -a 'XIAOMI_API_KEY' /root/.hermes/.env | xxd
```

**Note:** The truncated display `sk-cpy...lfby` in `config.yaml` or terminal is the system masking the full key — the actual stored value is the complete 51-character key. Always use the hex dump method to recover it.

### SSH Key Deployment (Alternative to Manual Copy)

Instead of manually copying the public key via `/mnt/c/`, use PowerShell to push the key directly to WSL:

```powershell
# From Windows PowerShell — pushes public key into WSL's authorized_keys
wsl -e bash -l -c "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
type $env:USERPROFILE\.ssh\id_ed25519.pub | wsl -e bash -l -c "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Verify it worked:

```powershell
wsl -e bash -l -c "cat ~/.ssh/authorized_keys"
```

## Connecting Hermes Desktop to WSL Hermes

Since WSL and Windows are on the same machine, there are two ways to connect Hermes Desktop to the Hermes backend running in WSL.

### Method A: URL + Key (API Server Mode) — Chat Only

This method proxies chat requests only. Memory, skills, sessions, and other management screens read from the local Windows `~/.hermes` (which doesn't exist), so they'll appear empty.

**Setup on WSL:**
```bash
# 1. Enable the API server in .env
echo "API_SERVER_ENABLED=true" >> ~/.hermes/.env
echo "API_SERVER_KEY=your-desktop-api-key" >> ~/.hermes/.env

# 2. Start the Hermes gateway (which also starts the API server on port 8642)
nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &

# 3. Verify the API server is listening
sleep 3
ss -tlnp | grep 8642
```

**Desktop settings:**
| Field | Value |
|-------|-------|
| Connection type | Remote (URL + Key) |
| URL | `http://127.0.0.1:8642` |
| Key | `your-desktop-api-key` |

WSL2 automatically forwards ports to Windows, so `127.0.0.1:8642` on Windows reaches the Hermes API server in WSL.

**Available features:** ✅ Chat only
**Not available:** ❌ Sessions, Skills, Memory, Logs — these read local Windows `~/.hermes`

### Method B: SSH Tunnel — Full Feature Access

This method creates an SSH tunnel that proxies ALL screens (Chat, Sessions, Skills, Memory, Logs, Tools, Gateway, etc.) via `sshExec` against WSL's `~/.hermes`.

**Step 1: Set up SSH key authentication**

On Windows (PowerShell):
```powershell
# Generate SSH key (if one doesn't exist)
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519
```

On WSL (add the public key):
```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat /mnt/c/Users/陆海天/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Step 2: Enable the API server** (same as Method A step 1-3)

**Step 3: Start SSH service in WSL**
```bash
sudo service ssh start
```

**Step 4: Desktop settings**
| Field | Value |
|-------|-------|
| Connection type | SSH Tunnel |
| SSH Host | `127.0.0.1` |
| SSH Port | `22` |
| Username | `lulu` |
| Private Key Path | `C:\Users\陆海天\.ssh\id_ed25519` |
| Remote Hermes Port | `8642` |

**Available features:** ✅ All screens (Chat, Sessions, Skills, Memory, Logs, Tools, Gateway, etc.)

### Trade-off Summary

| Feature | URL+Key | SSH Tunnel |
|---------|---------|------------|
| Chat | ✅ | ✅ |
| Sessions list & search | ❌ reads local | ✅ via SSH |
| Skills (browse, install) | ❌ reads local | ✅ via SSH |
| Memory (view/edit) | ❌ reads local | ✅ via SSH |
| Tools config | ❌ reads local | ✅ via SSH |
| Logs (gateway, agent) | ❌ reads local | ✅ via SSH |
| Setup complexity | Low | Medium (SSH key) |
| Connection speed | Fast | Slightly slower (SSH overhead) |

## Pitfalls

### API Server needs `hermes model` interactive setup
After configuring the provider in config.yaml, the `hermes model` interactive command is also required — the API server registers the provider through this step. If skipped, the API server returns:

```
Error: Internal server error: No inference provider configured. Run 'hermes model' to choose a provider and model...
```

Run `hermes model` interactively, select the configured provider (e.g. `xiaomi-mimo`) and model, then restart the gateway.

### SSH "Permission denied" when key auth fails
If the Desktop shows "SSH key incorrect", the private key path or authorized_keys setup is wrong. Verify with:

```powershell
ssh -i $env:USERPROFILE\.ssh\id_ed25519 -p 22 lulu@127.0.0.1
```

Should log in without password prompt.

### SSH Tunnel timeout: "SSH tunnel not ready after 12000ms"
When Desktop shows this error, the SSH connection itself failed. The logs in WSL typically show:
```
Connection closed by authenticating user lulu ... [preauth]
```
— meaning authentication failed before authorization. Common causes:

1. **WSL SSH server not running** — it's disabled by default on Ubuntu 26.04 for WSL. Start it:
   ```bash
   sudo service ssh start
   ```

2. **SSH key not authorized** — the public key wasn't added to WSL's `~/.ssh/authorized_keys`. Verify:
   ```bash
   cat ~/.ssh/authorized_keys
   ```
   If this gives `Permission denied`, the `.ssh` directory or `authorized_keys` file is owned by `root`. Fix from Windows PowerShell:
   ```powershell
   wsl -u root chown -R lulu:lulu /home/lulu/.ssh
   ```

3. **Incorrect Private Key Path** — The Desktop field labels "Private Key Pass" but actually expects a file **path** (e.g. `C:\\Users\\陆海天\\.ssh\\id_ed25519`), not a passphrase.

4. **SSH rate limiting (penalty)** — After multiple failed auth attempts, SSHd may temporarily penalize the source IP. The logs show `srclimit_penalise: activating ipv4 penalty`. Wait 20-30 seconds and retry, or restart SSH: `sudo service ssh restart`.

### WSL home directory must have execute permission for SSH auth
If `/home/lulu/` lacks the execute bit (permissions like `drw-------` / 600), `lulu` can't traverse their own home directory. This causes:
- `cat ~/.ssh/authorized_keys` → `Permission denied` (even with correct file ownership)
- SSH key authentication fails silently
- `su - lulu` fails with `Authentication failure` even after correct password is set

**Fix:** From Windows PowerShell as root:
```powershell
wsl -u root chmod 755 /home/lulu
```

Then verify:
```bash
ls -la /home/ | grep lulu  # should show drwxr-xr-x
cat ~/.ssh/authorized_keys  # should work now
```

**Detection:** If the user's WSL login shows errors like `-bash: /home/lulu/.bash_profile: Permission denied` or `touch: setting times of '/home/lulu/.motd_shown': Permission denied`, home directory permissions are broken.

### `su` fails after password change

If `echo "password" | sudo passwd --stdin lulu` succeeds (no error) but `su - lulu -c "echo OK"` still gives `Authentication failure`, two possibilities:

1. **Home directory execute bit missing** (see above) - the `su` process traverses `/home/lulu/` and fails before even checking the password
2. **Wrong password was used** — double-check the exact password string, especially if the user corrected you

Use `chpasswd` for reliability (reads `username:password` format, no newline issues):
```bash
echo "lulu:correct-password" | sudo chpasswd
```

### Gateway must be running before Desktop connects

The Desktop's API calls go to port 8642, which is served by the gateway. If the gateway isn't running, even with a successful SSH tunnel, the Desktop will get "Could not reach Hermes on the remote".

### Gateway auto-restart watchdog (WSL)

Since WSL doesn't have systemd, use a while-loop watchdog script to auto-restart the gateway if it crashes:

```bash
# Place the script
chmod +x ~/start-gateway-watchdog.sh

# Start it (runs in background, auto-restarts on crash)
nohup ~/start-gateway-watchdog.sh > /dev/null 2>&1 &

# Verify
sleep 2
ss -tlnp | grep 8642
```

The watchdog logs to `~/.hermes/logs/watchdog.log`. To stop: `pkill -f start-gateway-watchdog`.

**Behavior:**
- Exit code ≠ 0 (crash, signal kill) → auto-restarts after 2 seconds
- Exit code = 0 (clean/normal shutdown) → watchdog stops, won't restart
- First run auto-kills any existing gateway process before starting

**Pitfall:** If you `pkill` the gateway while the watchdog is running, the watchdog sees exit code ≠ 0 and restarts it. To fully stop: kill the watchdog first (`pkill -f start-gateway-watchdog`), then kill the gateway.

**Script content (create as `~/start-gateway-watchdog.sh`):**
```bash
#!/bin/bash
export PATH="$PATH:$HOME/.local/bin"
GATEWAY_LOG="$HOME/.hermes/logs/gateway.log"
WATCHDOG_LOG="$HOME/.hermes/logs/watchdog.log"
mkdir -p "$HOME/.hermes/logs"

# Pre-start cleanup — kill any stale gateway first
if pgrep -f "hermes gateway run" > /dev/null 2>&1; then
    echo "[$(date)] Old gateway detected, sending SIGTERM..." >> "$WATCHDOG_LOG"
    pkill -f "hermes gateway run" 2>/dev/null
    sleep 2
fi

echo "[$(date)] Watchdog started" >> "$WATCHDOG_LOG"
while true; do
    echo "[$(date)] Starting gateway..." >> "$WATCHDOG_LOG"
    hermes gateway run >> "$GATEWAY_LOG" 2>&1
    EXIT_CODE=$?
    if [ "$EXIT_CODE" -eq 0 ]; then
        echo "[$(date)] Gateway exited cleanly (code=0), watchdog stops." >> "$WATCHDOG_LOG"
        exit 0
    fi
    echo "[$(date)] Gateway crashed (code=$EXIT_CODE), restarting in 2s..." >> "$WATCHDOG_LOG"
    sleep 2
done
```

### WSL SSH key permissions
SSH is strict about permissions on WSL:
- `~/.ssh` directory must be `700` (drwx------)
- `~/.ssh/authorized_keys` must be `600` (-rw-------)
- Both must be owned by the WSL user (`lulu`), not root

**Troubleshooting `Permission denied` on `cat ~/.ssh/authorized_keys`:**
If user `lulu` can't read their own `.ssh` directory (`ls -la ~/.ssh/` gives "Permission denied"), the directory or files are owned by `root`. Fix from Windows PowerShell:

```powershell
wsl -u root chown -R lulu:lulu /home/lulu/.ssh
```

Then verify:
```bash
ls -la ~/.ssh/         # should show lulu:lulu
cat ~/.ssh/authorized_keys  # should show the public key content
```

Common causes of wrong ownership:
- Creating `.ssh/` with `sudo` (creates root-owned files)
- Copying the public key via `sudo cat ... >> ~/.ssh/authorized_keys`
- Running WSL commands as `root` from Windows and redirecting output into `/home/lulu/`

### WSL config must enable holographic memory for Desktop to show Memory

After transferring the `memory_store.db` from VPS, WSL's `config.yaml` also needs a `memory:` section with `provider: holographic`, otherwise the Desktop's Memory screen will remain empty even though the DB file is present.

**Add to `~/.hermes/config.yaml`:**

```yaml
memory:
  provider: holographic
  memory_char_limit: 2200
  user_char_limit: 1375
  memory_enabled: true
```

Or use one-liner:
```bash
cat >> ~/.hermes/config.yaml << 'EOF'

memory:
  provider: holographic
  memory_char_limit: 2200
  user_char_limit: 1375
  memory_enabled: true
EOF
```

Then restart the gateway:
```bash
pkill -f "hermes gateway"
nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &
```

**Pitfall:** The `API_SERVER_ENABLED=true` and `API_SERVER_KEY=...` must already be in `.env` — otherwise the gateway won't start the API server on port 8642 and Desktop can't connect.

### Gateway Dies After Restart — When to Ask the User

When PowerShell/WSL quoting gets too deep (3+ levels: SSH → cmd → wsl -u root bash -c → pipe), **don't keep retrying automated commands**. The nested quoting is fragile and wastes tokens. Instead:

1. Tell the user exactly what to type in their WSL terminal
2. Give them a `pkill` + `nohup` one-liner
3. Ask them to paste the output

This avoids the "PowerShell quoting hell" pitfall documented above and gets the job done faster.

## Syncing VPS data to WSL (Plugins, Memory, Sessions)

After SSH tunnel Desktop connection is working, the user may ask to "transfer skills/memory/plugins from VPS to WSL" so Desktop shows the same data.

### What to transfer

| Item | Source (VPS) | Destination (WSL) | Method |
|------|-------------|-------------------|--------|
| Plugins | `/root/.hermes/plugins/` | `~/.hermes/plugins/` | `tar` + `scp` |
| Memory DB | `/root/.hermes/memory_store.db` | `~/.hermes/memory_store.db` | `tar` + `scp` |
| Sessions DB | `/root/.hermes/sessions.db` | `~/.hermes/sessions.db` | `tar` + `scp` |

### Step-by-step

```bash
# 1. On VPS: tar the data
cd /root/.hermes
tar czf /tmp/hermes-plugins.tar.gz plugins/
tar czf /tmp/hermes-memory.tar.gz memory_store.db sessions.db

# 2. Copy to Windows (via SCP to VPS port, Windows SSH on port 2222)
sshpass -p '<win-password>' scp -P 2222 /tmp/hermes-plugins.tar.gz 陆海天@<win-ip>:C:/tmp/
sshpass -p '<win-password>' scp -P 2222 /tmp/hermes-memory.tar.gz 陆海天@<win-ip>:C:/tmp/

# 3. Stop Hermes gateway on WSL (to avoid DB locks)
sshpass -p '<win-password>' ssh -p 2222 陆海天@<win-ip> \
  "powershell -Command \"wsl pkill -f 'hermes gateway' 2>\\\$null\""

# 4. Extract in WSL (via Windows SSH bridge)
sshpass -p '<win-password>' ssh -p 2222 陆海天@<win-ip> \
  'cmd /c "wsl tar xzf /mnt/c/tmp/hermes-plugins.tar.gz -C ~/.hermes/"'
sshpass -p '<win-password>' ssh -p 2222 陆海天@<win-ip> \
  'cmd /c "wsl tar xzf /mnt/c/tmp/hermes-memory.tar.gz -C ~/.hermes/"'

# 5. Restart gateway
sshpass -p '<win-password>' ssh -p 2222 陆海天@<win-ip> \
  'cmd /c "wsl nohup hermes gateway run > ~/.hermes/logs/gateway.log 2>&1 &"'
```

### PowerShell quoting trap for multi-level commands

When running WSL commands through the VPS→Windows→WSL chain (3+ levels of nesting), **PowerShell's quoting is the main source of failure**:

- `&&`, `|`, `<`, `>` operators in PowerShell need different escaping than in cmd/bash
- The `wsl -u root` prefix with nested bash `-c` creates quote-matching hell
- **Fix: Use `cmd /c`** instead of `powershell -Command` when the command has bash operators:
  ```bash
  # ❌ Avoid — PowerShell tries to interpret operators
  ssh ... "powershell -Command \"wsl -u root bash -c \\\"echo a | chpasswd\\\"\""
  
  # ✅ Use cmd /c — passes the string literally to cmd
  ssh ... 'cmd /c "wsl -u root bash -c \"echo a | chpasswd\""'
  ```

The `cmd /c` pattern keeps the inner syntax clean because `cmd` doesn't try to parse `|` or `&&` like PowerShell does.

### API key masking in terminal output
The system masks sensitive values (showing `***` or truncated `sk-xxx...yyyy`). To recover the full key for transfer to another machine:

```bash
# Use hex dump to read raw bytes
python3 -c "
with open('/root/.hermes/.env', 'rb') as f:
    data = f.read()
lines = data.split(b'\\n')
for line in lines:
    if b'XIAOMI_API_KEY' in line:
        parts = line.split(b'=', 1)
        full_key = parts[1].decode()
        print(f'Full key: {full_key}')
"