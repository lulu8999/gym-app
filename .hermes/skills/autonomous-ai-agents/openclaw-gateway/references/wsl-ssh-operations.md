# SSH Operations: VPS → WSL → Windows Native

## Access Architecture

```
VPS (Hermes Agent) → Tailscale SSH → WSL (lulu@100.x.x.x) → WSL interop → Windows native (powershell.exe)
```

The VPS cannot SSH directly into Windows native (Tailscale routes port 22 to WSL only).

## Pattern: Run PowerShell on Windows Native from VPS

### Step 1: Write the script on VPS (as root)

```bash
write_file /tmp/check_stuff.ps1 << 'PSEOF'
Write-Host "=== System Info ==="
Get-ChildItem Env: | Where-Object { $_.Name -match "PATH" } | Format-Table
PSEOF
```

### Step 2: Base64 encode and transfer to WSL

```bash
B64=$(base64 -w0 /tmp/check_stuff.ps1)
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no lulu@<wsl-ip> \
  "echo '${B64}' | base64 -d > /mnt/c/Users/陆海天/check_stuff.ps1"
```

### Step 3: Execute via WSL interop

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no lulu@<wsl-ip> \
  "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Users/陆海天/check_stuff.ps1"
```

## Why not embed PowerShell directly in SSH?

- **Chinese character paths** (`C:\Users\陆海天\`) break in bash quoting
- **PowerShell's `$` and `|`** conflict with bash shell metacharacters
- **Nested quotes** cause syntax errors with `&`, `%`, `{`, `}`, etc.
- **`Where-Object` blocks** use `{}` that bash interprets as brace expansion

## Pitfalls

### 1. Write_file creates root-owned files on WSL

The VPS agent's `write_file` tool writes as root, so files placed on the WSL filesystem via `/mnt/c/` have root ownership. Fix by creating files via SSH heredoc:

```bash
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no lulu@<wsl-ip> \
  'cat > /tmp/script.ps1 << '\''EOF'\'' ... EOF'
```

### 2. `cmdkey` / Windows Credential Manager from WSL

OpenClaw stores API keys in Windows Credential Manager (Win32 only — not accessible from WSL). After migration, keys must be re-set on WSL:

```bash
openclaw auth set-provider deepseek --api-key <key>
```

### 3. Locked SQLite files during cleanup

Running OpenClaw gateway on Windows holds a lock on `state/openclaw.sqlite`. Use `Stop-Process` to kill the Node.js process before deleting:

```powershell
# Find openclaw-related Node process
Get-Process | Where-Object { $_.ProcessName -match "node" }

# Kill it
Stop-Process -Id <PID> -Force
```

## Reliable File Transfer (1-liner)

Copy script from VPS → Windows → WSL, execute, return output:

```bash
# Write ps1 on VPS
B64=$(base64 -w0 /tmp/script.ps1)
# Transfer to Win temp via WSL
sshpass -p '<pass>' ssh lulu@<ip> "echo '${B64}' | base64 -d > /tmp/script.ps1 && cp /tmp/script.ps1 /mnt/c/Users/陆海天/script.ps1"
# Execute
sshpass -p '<pass>' ssh lulu@<ip> "powershell.exe -File C:/Users/陆海天/script.ps1"
```
