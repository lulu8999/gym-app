# `__import__('module.submodule')` Returns Top-Level Module

## Background

Encountered during Hermes model-watchdog development. A standalone Python watchdog script used `__import__('urllib.request')` to avoid typing imports at the top. This failed because `__import__` returns the **top-level package**, not the requested submodule.

## The Bug

```python
# File: /root/scripts/model_watchdog.py (original version)

def test_api(provider, base_url, api_key):
    req = __import__('urllib.request').Request(        # ❌
        url, headers={"Authorization": f"Bearer {api_key}"})
    resp = __import__('urllib.request').urlopen(req)    # ❌
```

Error:
```
module 'urllib' has no attribute 'Request'
```

## Root Cause

`__import__('urllib.request')` in Python 3:
1. Imports `urllib` (top-level package)
2. Imports `urllib.request` (submodule)
3. **Returns `urllib`**, NOT `urllib.request`

This is by design (PEP 302). `__import__` is a low-level function meant for import hooks, not for regular code.

## The Fix

Replace with standard imports at the top of the file:

```python
import urllib.request  # ✅
import fcntl           # ✅ (also fix: __import__('fcntl'))

def test_api(...):
    req = urllib.request.Request(...)
    resp = urllib.request.urlopen(req)
```

Or use `importlib.import_module`:

```python
import importlib
req_mod = importlib.import_module('urllib.request')
req = req_mod.Request(...)
```

## Key Lesson

In standalone Python scripts (especially scripts run by cron or systemd), **use standard `import` statements at the top level**. The `__import__` function exists for meta-programming (plugin loaders, import hooks) — not for regular tool code. The "save a line of code" trade-off is not worth the bug surface.

## Debugging Trail

- First symptom: watchdog said "FAIL" but direct Python test passed
- Added `except Exception as e: print(e)` → revealed `module 'urllib' has no attribute 'Request'`
- Changed to `import urllib.request` → fixed
- Same issue found with `__import__('fcntl')` → changed to `import fcntl`
