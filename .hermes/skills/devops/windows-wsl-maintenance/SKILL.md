---
name: windows-wsl-maintenance
category: devops
description: Manage Windows and WSL interop — disk cleanup, app management, Hermes deployment on WSL, Hermes Desktop connection setup (API Server + SSH Tunnel), Windows SSH bridge into WSL, and remote administration of the Win+WSL dual environment from a VPS.
trigger: user asks to clean up, inspect disk space, find a hidden program, remove stubborn software, manage installed applications on a Windows machine, install/config Hermes on WSL, or connect Hermes Desktop to a WSL Hermes backend
---

# Windows WSL Maintenance

## Trigger

User asks to:
- "看看C/D/E盘有什么" (disk space analysis)
- "清理/删掉" specific apps or files
- Find a background program / malware
- Optimize or free up disk space
- Install or configure software in WSL (Hermes, Node.js, etc.)
- Access WSL from a remote machine (VPS) when WSL SSH is down

## Prerequisites

- WSL is installed and SSH-accessible (or direct WSL terminal)
- SSH connection: `sshpass -p '<password>' ssh -o StrictHostKeyChecking=no lulu@<win-ip>`
- Windows drives are mounted under `/mnt/c`, `/mnt/d`, `/mnt/e` in WSL
- PowerShell accessible via `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe`
- For Node.js/npm tasks: See [WSL NVM Setup](references/wsl-nvm-setup.md) for installation and loading requirements

## Workflow

### 1. Disk Inventory

List top-level directories with sizes:
```bash
# E drives
ls /mnt/e/
du -sh /mnt/e/*/ 2>/dev/null | sort -rh
# Or for specific directories when full scan is too slow:
timeout 30 du -sh /mnt/e/target_dir/ 2>/dev/null
```

Check total disk usage:
```bash
df -h /mnt/c/ /mnt/d/ /mnt/e/
```

### 2. Find Installed Software

Query registered uninstall entries (64-bit + 32-bit):
```powershell
powershell.exe -NoProfile -Command "Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' | Select-Object DisplayName, Publisher, InstallLocation, UninstallString | Format-Table -AutoSize -Wrap"
```

Also check 32-bit:
```powershell
powershell.exe -NoProfile -Command "Get-ItemProperty 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' | ..."
```

### 3. Find Hidden / Background Programs

Query running processes with window titles (reveals tray apps):
```powershell
powershell.exe -NoProfile -Command "Get-Process | Where-Object { \$_.MainWindowTitle -ne \"\" } | Select-Object ProcessName, MainWindowTitle, Id"
```

Query system tray / notification area processes by name:
```powershell
powershell.exe -NoProfile -Command "Get-Process | Where-Object { \$_.ProcessName -match 'notify|tray|tool|tip|pop|alert' }"
```

Find exact process path (for malware):
```powershell
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name = 'suspicious.exe'\" | Select-Object ProcessId, ExecutablePath, CommandLine"
```

List ALL startup entries (registry + folder):
```powershell
powershell.exe -NoProfile -Command "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User | Format-Table -AutoSize -Wrap"
```

### 4. Remove Stubborn Malware / Locked Programs

Some programs protect themselves with service registrations, permission-locked files, and running processes. Follow this order:

**4a. Find all services**:
```powershell
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Service | Where-Object { \$_.PathName -match 'malwareDir' } | Select-Object Name, DisplayName, PathName, StartMode, State"
```

**4b. Stop and delete services**:
```powershell
# Stop
Stop-Service ServiceName -Force
# Delete service registration
sc.exe delete ServiceName
```

**4c. Kill all related processes**:
```bash
# From WSL bash
taskkill /F /IM process.exe /T
# Or from PowerShell
powershell.exe -NoProfile -Command "Get-Process | Where-Object { \$_.ProcessName -match 'pattern' } | Stop-Process -Force"
```

**4d. Remove permission locks**:
```bash
# From WSL — may fail on locked files
rm -rf /mnt/c/Users/陆海天/AppData/Local/malwareDir/
```

When `rm -rf` gives "Permission denied" or "Input/output error", use PowerShell:
```powershell
# Take ownership + grant full control + delete
takeown /f "C:\path\to\dir" /r /d y
icacls "C:\path\to\dir" /grant "用户名:(OI)(CI)F" /T /Q
Remove-Item "C:\path\to\dir" -Recurse -Force
```

If files are still locked, find and kill the holding process first:
```powershell
# Check what's still running
Get-Process | Where-Object { $_.Path -match "malwareDir" }
```

**4e. For unlockable DLLs/databases** — find what process has the handle:
- WeChat database files (.db, .db-shm, .db-wal) are locked when WeChat is running → kill WeChat process first
- Kill all relevant processes before attempting deletion

### 5. Clean Temp Files

Safe to delete:
```bash
rm -rf /mnt/c/Windows/Temp/*
rm -rf /mnt/c/Users/陆海天/AppData/Local/Temp/*
```

Check sizes first:
```bash
du -sh /mnt/c/Windows/Temp/ /mnt/c/Users/陆海天/AppData/Local/Temp/
```

### 6. Uninstall Normal Apps

For MSI-installed apps (from GUID):
```bash
/mnt/c/Windows/System32/msiexec.exe /x {GUID} /quiet /norestart
```
Note: Use longer timeout (120s+) for MSI uninstalls — they may take a while.

For EXE uninstallers found in the directory itself:
```bash
/path/to/Uninstall.exe /S  # silent switch
```

## 🚨 绝对禁区（碰就算违规）

### 6. Clean Recycle Bin
```bash
rm -rf /mnt/d/\$RECYCLE.BIN/*
rm -rf /mnt/e/\$RECYCLE.BIN/*
```

### Disk Cleanup Procedure

Full C drive cleanup workflow (scan → categorize → clean with confirmation):
📕 `references/windows-disk-cleanup-procedure.md`

## File Conversion on WSL (ncm / audio / media)

When the user needs to convert files stored on Windows using Linux tools through WSL:

See [WSL File Conversion](references/wsl-file-conversion.md) for the full workflow including:
- Cross-machine file transfer (VPS → Windows Temp → WSL)
- Pre-compiled binary installation via SSH bridge
- Proxy usage for GitHub downloads (VPS can't reach GitHub directly)
- Batch conversion patterns using `*.extension` wildcard in deeply-nested SSH calls

## Gateway Auto-Restart Watchdog (WSL)

For auto-restarting the Hermes gateway on WSL (no systemd), use the watchdog script at `scripts/start-gateway-watchdog.sh` in this skill directory. See the "Gateway auto-restart watchdog" section in `references/hermes-install-wsl.md` for usage.

## Remote VPS → Windows/WSL Connection

### Primary: Tailscale + WSL SSH (port 22) ✅

The **preferred** method. Direct SSH into WSL via Tailscale — fast, stable, no escaping hell.

```bash
# First, check Tailscale device status
tailscale status

# Connect to WSL directly
sshpass -p '20040422lht' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 lulu@100.80.251.96
```

| Parameter | Value |
|-----------|-------|
| Tailscale IP | `100.80.251.96` |
| Port | `22` |
| User | `lulu` |
| Password | `20040422lht` |

### Fallback: Windows SSH Bridge (port 2222)

Only when WSL SSH is down. Goes through Windows native SSH → PowerShell → `wsl` commands.

```bash
sshpass -p '20040422lht' ssh -p 2222 陆海天@100.80.251.96 "powershell -Command \"wsl <command>\""
```

See [Windows SSH Bridge to WSL](references/windows-ssh-bridge-to-wsl.md) for full reference.

### ⚠️ Connection troubleshooting: Tailscale-first

When user says "连到我电脑/Win/WSL":
1. **Run `tailscale status` first** — get the Tailscale IP immediately
2. SSH directly to WSL on port 22
3. If refused/timeout, try port 2222 (Windows SSH bridge)
4. 3 consecutive timeouts → tell user to check Tailscale/network

**❌ Never try**: `localhost`, `127.0.0.1` (that's VPS itself), or random LAN IPs

## SSH Password Change (Non-interactive)

When the user asks to change SSH passwords across Windows + WSL, use this pattern:

### Windows (native OpenSSH, port 2222)
```bash
sshpass -p '<old-password>' ssh -p 2222 陆海天@<win-ip> \
  "powershell -Command \"net user 陆海天 <new-password>\""
```
`net user` needs no old password when run as admin — `陆海天` is admin so it just works.

### WSL (port 22, via netsh forwarding)
```bash
printf '<old-password>\n<new-password>\n<new-password>\n' | \
  sshpass -p '<old-password>' ssh lulu@<win-ip> passwd
```
The `printf` feeds the interactive `passwd` prompt: old → new → confirm.

### Verification
```bash
# WSL
sshpass -p '<new-password>' ssh lulu@<win-ip> "echo OK"
# Windows
sshpass -p '<new-password>' ssh -p 2222 陆海天@<win-ip> "echo OK"
```

⚠️ **macOS limitation**: This does NOT work on modern macOS (Sequoia 15+) — see `macos-server-setup` skill for details.

## Pitfalls

- **SSH 连不上时的系统化排查** → 见 `references/windows-ssh-port-diagnostics.md`（端口扫描、错误类型诊断、Tailscale relay 超时处理）
- **SSH to WSL can be slow** on NTFS directories with many files. Use `timeout N` to cap each `du` call. Prefer querying specific directories over full scans.
- **Chinese characters in paths**: 陆海天 (the user's Windows account) often causes issues in bash. Use PowerShell for paths with Chinese characters when WSL fails.
- **PowerShell escaping**: `$` must be escaped as `\\$` when passed through bash, and `"` must be handled carefully. Use single quotes around the PowerShell command in bash where possible, or escape properly.
- **du is painfully slow on NTFS** via WSL. For large drives (E: 1TB), full scans can timeout. Target specific directories instead.
- **WSL CMD.exe UNC path issue**: cmd.exe launched from WSL inherits the WSL UNC path (`\\\\wsl.localhost\\...`) which Windows CMD can't handle. Use `pushd C:\\` first or write a batch file to `C:\\tmp\\`.
- **Processes with Chinese names**: `Get-Process` may show garbled characters for Chinese-named processes in PowerShell over SSH.
- **Do NOT kill WeChat/Weixin without warning** — the user may lose unsaved messages. If locked files are WeChat DBs, tell the user to close WeChat manually first.
- **360MoveData** often contains WeChat database backups — these are locked when WeChat runs. Kill WeChat process first.
- **Ctrl+V doesn't paste in WSL native terminal**. Use **right-click** (paste on click) or **Shift+Insert**. For full clipboard support, use **Windows Terminal** (Microsoft Store) which supports Ctrl+Shift+V and proper copy/paste.
- **DO NOT SSH into WSL from the same Windows machine** — just open WSL directly via cmd (`wsl`), PowerShell (`wsl`), or Ubuntu app. Only SSH into WSL from a remote machine (e.g. VPS).
- **WSL SSH disabled by default** — Ubuntu 26.04 for WSL has SSH service `disabled` and `inactive`. Start with `sudo service ssh start` (or `wsl -u root service ssh start` from Windows PowerShell).
- **WSL home directory permissions** — `/home/lulu/` can lose its execute bit (`drw-------` / 600), breaking SSH key auth and all file reads. Fix with `wsl -u root chmod 755 /home/lulu` from Windows PowerShell.
- **Hermes Desktop SSH Tunnel timeout** — "SSH tunnel not ready after 12000ms" typically means WSL SSH is not running (see above), SSH keys aren't authorized, or `/home/lulu/` lacks execute permission. See `references/hermes-install-wsl.md` for full SSH tunnel setup and troubleshooting.
- **PowerShell `wsl -e bash -l -c` pattern** — Use this for running Hermes commands via the SSH bridge when PATH isn't set up in non-interactive shells. The `-l` (login) flag sources `.bashrc`/`.bash_profile` which adds `~/.local/bin` to PATH.\n- **PowerShell quoting for 3+ level nesting** — When going VPS → Windows SSH → WSL bash (3 levels), PowerShell's `&&`, `|`, `<` get interpreted as PowerShell operators and break the command. **Use `cmd /c` instead of `powershell -Command`** for the outer wrapper when the command contains bash operators. Example: `ssh ... 'cmd /c \"wsl tar xzf ... -C ~/.hermes/\"'`.
- **Memory DB transfer needs `memory: provider: holographic` config** — Copying `memory_store.db` to WSL is not enough. WSL's `config.yaml` must also have a `memory:` section with `provider: holographic` (see `references/hermes-install-wsl.md`). Without it, the Desktop's Memory screen stays empty.
- **🔴 VPS → Windows SSH 前必须先确认网络可达** — 从 VPS SSH 到 Windows/WSL 之前，先确认 Windows 机器有公网 IP 或已配置内网穿透（Tailscale/frp/Cloudflare Tunnel）。不要盲目尝试 IP 地址——VPS 自己的内网 IP（如 10.0.0.x、100.80.x.x）不是 Windows 机器的 IP。正确做法：① 先问用户 Windows 的可达 IP 或 Tailscale IP ② 或先 `ping` / `curl` 验证连通性 ③ 连续 3 次超时/拒绝后停下来问用户检查网络，不要无限重试。
