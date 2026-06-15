# Remote File Organization via Windows SSH

Copy, deduplicate, and classify files on a Windows machine from Linux over SSH.

## Core Approach

| Step | How |
|------|-----|
| Write script | Write Python on VPS → SCP to Windows (`F:\` or `C:\tmp\`) |
| Execute | `sshpass ... E:\Python\python.exe F:\script.py` |
| Background | Set `background=true, notify_on_complete=true` for long ops |

## Why Python Over PowerShell Over SSH

**PowerShell via SSH is quoting hell.** `$`, backtick, single/double quote nesting across bash→SSH→PowerShell breaks constantly.

| Method | Verdict |
|--------|---------|
| Inline `powershell -Command "..."` via SSH | ❌ Breaks on `$`, `'`, `` ` ``, Japanese/Chinese chars |
| `.ps1` file on Windows | ❌ UTF-8 encoding issues, `ExecutionPolicy` blocks |
| **Python `.py` file** | ✅ Clean, handles UTF-8/Chinese natively, no quoting issues |

## Workflow

```bash
# 1. Write Python script on VPS
write_file /tmp/organize.py

# 2. SCP to Windows (avoid Chinese paths in SSH args)
sshpass -p 'password' scp -P 2222 /tmp/organize.py user@host:'F:\script.py'

# 3. Execute (use absolute Python path)
sshpass -p 'password' ssh -p 2222 user@host "E:\Python\python.exe F:\script.py"

# 4. For long ops, use background + check periodically
sshpass -p 'password' ssh ... "E:\Python\python.exe F:\script.py > F:\result.txt 2>&1" &
sleep 30 && sshpass ... "type F:\result.txt"
```

## Key Patterns

### File Scanning
```python
from pathlib import Path
src = Path(r'C:\Users\陆海天\Desktop\mp3')
mp3s = list(src.glob('*.mp3'))
```

### Extract Song Title From "Artist - Title.ext"
```python
def extract_title(filename):
    name = filename.stem
    idx = name.rfind(' - ')
    return name[idx+3:].strip() if idx >= 0 else name.strip()
```

### Detect Chinese in Title
```python
def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf]', text))
```

### Dedup by Title
```python
seen = {}
for item in all_files:
    if item['title'] not in seen:
        seen[item['title']] = item
deduped = list(seen.values())
```

### Copy With Progress
```python
for i, item in enumerate(deduped):
    shutil.copy2(item['path'], dest_dir / item['path'].name)
    if (i+1) % 20 == 0:
        print(f'Progress: {i+1}/{len(deduped)}', flush=True)
```

## Pitfalls

### USB Drive Speed
USB flash drives can be **very slow** for many small files (5+ minutes for 100 files ~1GB). Use background mode and check periodically.

### `flush=True` Is Critical for Background Scripts
When running Python via SSH in background (`> result.txt 2>&1`), stdout is fully buffered. Print statements won't appear in the log file until the buffer fills up or the script exits. **Always add `flush=True` to `print()`** when you want real-time progress visibility:

```python
print('Progress: %d/%d' % (i, total), flush=True)
```

Without `flush=True`, the result file stays empty until the script finishes or hangs — making debugging impossible.

### "File Not Found" After Successful Glob
If `Path.glob('*.ncm')` finds 133 files but `shutil.copy2()` throws `[WinError 2]` on most of them:
- The U盘 may have been briefly disconnected (reconnecting resets file handles)
- A prior Python process (killed mid-operation) may have left stale handles
- **Fix**: verify source files are still accessible right before each copy, not just during the initial scan

### File Not Found After Scan
If Python `glob()` finds files but `shutil.copy2()` says "file not found":
- The USB drive may have been disconnected/reconnected between scan and copy
- Previous interrupted script may have left handles stale
- **Fix**: redo scan and copy in the same loop without pre-scaling

### Chinese Filenames on Windows
- Python reads them correctly from filesystem when running as a `.py` file
- Inline `python -c "..."` often breaks due to SSH quoting mangling Unicode
- Always write script to file → SCP → execute

### SSH Command Timeout
Default timeout (180s) may not be enough for USB copy ops. Either:
- Background mode with `notify_on_complete=true`
- Increase timeout via `terminal(timeout=600)` (max 600s foreground)

### Long-Running Scripts: `start /b` Background Pattern
When a Python script times out over SSH (e.g. copying 100+ files to USB), run it in background:

```bash
# Start in background, redirect output to file
sshpass -p '密码' ssh -p 2222 陆海天@<win-ip> \
  "start /b E:\Python\python.exe F:\script.py > F:\result.txt 2>&1 & echo STARTED"

# Poll results periodically
sleep 30 && sshpass ... "type F:\result.txt"
sleep 30 && sshpass ... "type F:\result.txt"

# Check if still running
sshpass ... "tasklist | findstr python"
```

**⚠️ `start /b` vs SSH foreground:**
- SSH foreground has timeout limits (default 180s, max 600s)
- `start /b` detaches the process from the SSH session — survives timeout/disconnect
- Output must be redirected (`> file 2>&1`) since there's no terminal
- Poll with `type result.txt` — empty file means still running or no output yet

**⚠️ `flush=True` in background Python:**
When running via `start /b`, Python stdout is fully buffered. Add `flush=True` to all `print()` calls:
```python
print('Progress: %d/%d' % (i, total), flush=True)
```
Without this, `result.txt` stays empty until script finishes.

## Check Progress

```bash
# Count files in dest
sshpass ... 'dir /a-d F:\中文\ | findstr /i "个文件"'

# Check if script still running
sshpass ... 'tasklist | findstr python'

# Read partial results
sshpass ... 'type F:\result.txt'
```