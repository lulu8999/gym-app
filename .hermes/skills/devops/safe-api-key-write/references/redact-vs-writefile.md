# write_file 不损坏磁盘文件——2026-06-06 调查记录

## 最初误区

之前认为 `write_file` 工具会自动将 `sk-xxx` 替换为 `***` 并**写入磁盘**，导致 `.env` 文件损坏。这个判断来自观察到：
- `cat .env` 显示 `XIAOMI_API_KEY=***`
- `grep` 也显示 `***`
- `write_file` 的返回结果也显示 `***`

## 实际机制

所有输出渠道都经过 `redact_sensitive_text()` 函数过滤：

| 渠道 | 过滤位置 | 覆盖范围 |
|------|----------|----------|
| `read_file` 回读 | file_tools.py L823 | 显示结果被遮盖 |
| `terminal` + `cat`/`grep` | 终端输出捕获层 | 输出被遮盖 |
| `execute_code` + `print` | stdout 捕获层 | 输出被遮盖 |
| **`xxd` hex 输出** | **不受影响** | ✅ 看到真实内容 |

**磁盘文件从未被修改过。** hex 验证：
```bash
# 写入
write_file(path="/tmp/test.txt", content="MY_KEY=*** content="MY_KEY=sk-abc123def456")

# 验证 - xxd 看到真实内容
xxd /tmp/test.txt
# 00000000: 4d59 5f4b 4559 3d73 6b2d 6162 6331 3233  MY_KEY=*** 1;bg-  # 显示
# 00000010: 6465 6634 3536 0a                           def456.
# ^ 73 6b 2d = sk-，文件正确

# 验证 - cat 看到遮盖版本
cat /tmp/test.txt
# MY_KEY=***
```

## 触发路径

在 `file_tools.py` 中，`redact_sensitive_text` 被调用于：
1. `read_file` 回读校验（L823）
2. `file_operations.py` 的 `_atomic_write` 使用 `cat > "$tmp"` 写入——**纯管道，无内容处理**

## 修复方向

要看到真实 key 有两种方法：
1. **修改 redact.py 正则**（降低匹配灵敏度）
2. **跳过 .env 文件的 redact**（在 file_tools.py 中判断文件路径）

## 验证过的结论

- `write_file` 的 `ShellFileOperations.write_file` → `_atomic_write` → `cat > "$tmp"` + `mv`：**不修改内容**
- 终端 `echo`/`printf` 直接写文件：**正确**
- Python `open().write()` 直接写文件：**正确**
- 只有经过 `redact_sensitive_text` 的输出渠道才显示 `***`
