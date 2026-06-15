# Windows SSH Bridge to WSL

Access WSL from a remote Linux host (e.g. VPS) via Windows native SSH when WSL's own SSH server is down.

## The Pattern

```
VPS ──SSH(2222)──→ Windows ──powershell──→ wsl command
```

Use this when:
- WSL SSH server is inactive/stopped
- You need to run WSL commands but can't reach WSL directly

## Connection

```bash
sshpass -p '<win-password>' ssh -p 2222 陆海天@<win-ip> "powershell -Command \"wsl command\""
```

Replace `<win-password>` with Windows login password (6 spaces for Lulu's setup).

## Examples

### Check WSL Hermes config
```bash
sshpass -p '      ' ssh -p 2222 陆海天@100.80.251.96 "powershell -Command \"wsl cat ~/.hermes/config.yaml\""
```

### Start WSL SSH server
```bash
sshpass -p '      ' ssh -p 2222 陆海天@100.80.251.96 "powershell -Command \"wsl -u root service ssh start\""
```

### Run any WSL command
```bash
sshpass -p '      ' ssh -p 2222 陆海天@100.80.251.96 "powershell -Command \"wsl ls -la\""
```

## Pitfalls

- **Piping through cmd.exe**: Commands like `| head -5` or `| more` don't work because the pipe is interpreted by Windows cmd.exe, not WSL bash. Use `powershell -Command "wsl command | Select-Object -First N"` instead.
- **Chinese characters in output**: Windows SSH with cmd.exe produces garbled Chinese output. This is cosmetic — the command itself runs correctly.
- **WSL SSH inactive by default**: On Ubuntu 26.04 LTS for WSL, SSH service is `disabled` and `inactive`. Start with `wsl -u root service ssh start` if needed.
- **PowerShell escaping**: Nested quotes need careful escaping. Pattern: `"powershell -Command \"wsl command\""` (outer double quotes for SSH, inner backslash-escaped for the command string).
- **Exit code 1 on Select-Object**: PowerShell's `Select-Object -First N` returns exit code 1 when the source stream is exhausted (not an error). Check the actual output, not the exit code.