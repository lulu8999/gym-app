# WSL Environment Setup - NVM & Node.js

## Installing Node.js via NVM in WSL

### Step 1: Install NVM
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
```

### Step 2: Load NVM (immediate use)
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
```

### Step 3: Install Node.js LTS
```bash
nvm install --lts
```

### Step 4: Verify
```bash
node --version   # e.g., v24.16.0
npm --version    # e.g., 11.13.0
```

## ⚠️ Critical: NVM Loading Requirement

After installing NVM, `node` and `npm` commands won't work in new SSH sessions unless you:
1. **Source NVM first**: `source ~/.nvm/nvm.sh`
2. **Or**: Add to `~/.bashrc` (already done by NVM installer, but needs new terminal)

**Workaround for scripts**: Always prefix commands with `source ~/.nvm/nvm.sh &&` when running via SSH.

Example:
```bash
sshpass -p '111111' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96 "source ~/.nvm/nvm.sh && node --version"
```

## Transferring Scripts/Configs to WSL

### From VPS to WSL (via SSH)
```bash
# Create directory
sshpass -p '111111' ssh -o StrictHostKeyChecking=no lulu@<win-ip> "mkdir -p ~/scripts"

# Write file via heredoc
sshpass -p '111111' ssh -o StrictHostKeyChecking=no lulu@<win-ip> "cat > ~/scripts/script.ps1 << 'EOF'
# script content here
EOF"

# Or copy from VPS
scp /path/to/file lulu@<win-ip>:~/scripts/
```

### Copy to Windows Desktop (from WSL)
```bash
cp ~/scripts/file.bat /mnt/c/Users/陆海天/Desktop/
```

## Creating MEMORY.md in WSL

A good pattern for tracking configuration across sessions:

```bash
cat > ~/MEMORY.md << 'EOF'
# WSL Configuration Memory

## System Info
- User: lulu
- OS: Ubuntu 26.04 LTS
- Python: 3.14.4
- Node.js: v24.16.0 (NVM)

## SSH Config
- WSL SSH: Port 22, user lulu, password 111111
- Windows SSH: Port 2222, user 陆海天, password 6 spaces

## Important Directories
- ~/scripts/ - Script storage
- ~/.openclaw/ - OpenClaw config
- ~/.nvm/ - NVM config

## Installed Software
- Node.js v24.16.0 (npm 11.13.0)
- Python 3.14.4
- OpenClaw

## Notes
- Need `source ~/.nvm/nvm.sh` before using node/npm
EOF
```

## Common Issues

### Node.js not found after SSH login
- **Cause**: NVM not loaded in non-interactive shell
- **Fix**: `source ~/.nvm/nvm.sh && node --version`

### PowerShell commands fail from WSL
- **Cause**: WSL PowerShell has no admin rights
- **Fix**: Use Windows native SSH (port 2222) for admin tasks

### File permissions when copying to Windows
- **Issue**: Files copied to `/mnt/c/` may lose execute permissions
- **Fix**: Use `chmod +x` on the WSL side, or set permissions in Windows
