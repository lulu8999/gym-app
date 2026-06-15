# write_file sk-xxx 替换 Bug 复现方法

## 问题描述

Hermes Agent 的 `write_file` 工具在写入文件时，会自动将 `sk-` 开头的 API Key 替换为 `***`。这不是显示遮罩——**磁盘上的文件内容确实被改坏了**。

## 复现步骤

### 1. 用 write_file 写入含 sk-xxx 的文件

```
write_file(path="/tmp/test_key.txt", content="TEST_API_KEY=sk-tes123456789abcdef")
```

### 2. 检查磁盘上的实际内容

```bash
od -c /tmp/test_key.txt | head -3
# 期望: T E S T _ A P I _ K E Y = s k - t e s 1 2 3 4 5 ...
# 实际: T E S T _ A P I _ K E Y = * * *
```

### 3. 对比终端写入（不受影响）

```bash
printf 'TEST_API_KEY=sk-tes123456789abcdef\n' > /tmp/test_key_terminal.txt
od -c /tmp/test_key_terminal.txt | head -3
# 结果: T E S T _ A P I _ K E Y = s k - t e s 1 2 3 4 5 ... ✅
```

### 4. 验证 write_file 的字节数

```
bytes_written: 22   ← 只有 "TEST_API_KEY=***" 的长度
```

而原始内容 `TEST_API_KEY=sk-tes123456789abcdef` 应该是 38 字节。

## 结论

- `write_file` → 磁盘内容被替换（22 字节 vs 38 字节）
- `patch` (find-and-replace) → 磁盘内容正确 ✅（不触发替换逻辑）
- `terminal` + `printf`/`echo` → 磁盘内容正确（仅显示被遮罩）
- `set_env_key.py`（Python 文件操作）→ 磁盘内容正确 ✅
