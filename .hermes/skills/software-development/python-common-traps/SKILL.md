---
name: python-common-traps
description: "Common Python gotchas — import quirks, syntax traps, and runtime surprises encountered in Hermes/CLI development"
version: 1.0.0
author: Lulu
tags: [python, traps, import, debugging, gotchas]
---

# Python Common Traps

A collection of Python language-level traps that bite during script/CLI development. Each entry has: symptom, root cause, fix, and detection trick.

## Import Traps

### `__import__('urllib.request')` 返回 `urllib` 而不是 `urllib.request`

**Symptom:** `AttributeError: module 'urllib' has no attribute 'Request'`

**Cause:** Python 3 的 `__import__` 导入整个包树后返回**顶层包**，不是请求的子模块。

**Fix:**
```python
import importlib
mod = importlib.import_module('urllib.request')  # ✅
mod.Request  # works

# Or just:
import urllib.request  # ✅ clearer
```

**Detection:**
```python
print(__import__('os.path').__name__)     # 'os' — not 'os.path'
print(importlib.import_module('os.path').__name__)  # 'os.path'
```

**Reference:** `references/python-import-trap.md` in model-watchdog skill.

### `from X import *` in submodule

**Symptom:** "Name not defined" after star-import from a submodule.

**Cause:** `__all__` not defined; Python only exports names without leading `_`. If `__all__` IS defined, only those names are exported — even if they don't exist yet.

**Fix:** Always define `__all__` explicitly in `__init__.py`.

### Stale module cache in REPL debugging

**Symptom:** You edit a file (e.g. `app.py`), re-import in the same Python REPL, but old behavior persists. Flask test client shows different results than calling the same function directly.

**Cause:** Python caches imported modules in `sys.modules`. A second `from app import function` in the same process skips the filesystem and returns the already-loaded module.

**Fix:**
```python
# Force re-import
import sys
for mod in list(sys.modules.keys()):
    if 'app' in mod:
        del sys.modules[mod]
from app import app, get_sessions_for_user
```

**Detection trick:**
```python
# Check if it's cached
import sys
print('app' in sys.modules)  # True = cached, re-load won't see disk changes
```

**Works for:** Flask test clients, pytest reload, Jupyter notebooks, any multi-import REPL workflow.

---

## Shell / Subprocess Traps

### `shlex.split()` 不够用

**Symptom:** `subprocess.run(cmd.split(...))` fails on quoted args.

**Fix:** Always use `shlex.split()` for user-provided command strings, or pass a list directly. Never `str.split()`.

---

## String / Encoding Traps

### `urllib.request.Request` 遇中文 URL 报 ASCII 编码错误

**Symptom:** `UnicodeEncodeError: 'ascii' codec can't encode characters in position X-Y: ordinal not in range(128)`

**Cause:** `urllib.request.Request(url)` 默认用 ASCII 编码 URL 字符串。当 URL 路径含中文字符（如 GitHub raw 链接 `/滑稽大佬/xxx.gif`）时，ASCII 无法编码中文，抛出异常。

**Fix:**
```python
from urllib.parse import urlparse, quote

parsed = urlparse(url)
# 对路径部分编码（保留 / 和 .）
encoded_path = quote(parsed.path, safe='/.')
encoded_url = f'{parsed.scheme}://{parsed.netloc}{encoded_path}'
req = urllib.request.Request(encoded_url, headers={...})
```

**Detection:** 错误信息包含 `ordinal not in range(128)` 且指向 URL 处理代码。

**Note:** `requests` 库不受影响（自动处理 URL 编码），只在使用 `urllib.request` 时出现。

### 中文/智能引号导致字符串提前闭合

**Symptom:** `SyntaxError: invalid character '》' (U+300B)` — 语法错误指向字符串外部的字符。

**Cause:** 字符串用 ASCII 单引号 `'` 包裹，但内容中包含中文书名号 `》` 前面有右单引号 `'`（U+2019）。Python 将 `'` 误判为字符串结束，导致后面的 `》` 变成未定义符号。

```python
# ❌ 错误 — 内容含右单引号 '，与分隔符 ' 冲突
['披头士时期', '1967年', '《Sgt. Pepper's》专辑发行']
# Python 解析为: '《Sgt. Pepper' + s》专辑发行' → 语法错误

# ✅ 正确 — 用双引号包裹
["披头士时期", "1967年", "《Sgt. Pepper's》专辑发行"]

# ✅ 也可以 — 转义内部引号
['披头士时期', '1967年', '《Sgt. Pepper\'s》专辑发行']
```

**Detection:** 错误信息指向中文标点（`》`、`》`）或看似正常的英文字符，大概率是引号嵌套问题。

**预防:** 含中文内容的列表/字典一律用双引号 `"` 做字符串分隔符，避免与中文的 `'` `'` 冲突。

### `strip("'\"")` 会去掉所有前导/尾随的引号字符

**Symptom:** `.env` 里的 Key 值被截断（当 Key 本身包含特殊字符时）。

**Fix:** Only strip from the known structure (e.g., shell lines) — never blindly strip when the value format is unknown.

---

## When Not to Use This Skill

- Debugger workflows → use `python-debugpy` skill
- Systematic root-cause debugging → use `systematic-debugging` skill
- Test failures → use `test-driven-development` skill
- Environment-specific errors (missing packages, wrong versions) → not language traps
