# .env 清理标准流程

## 适用场景

- `.env` 文件过于庞大（注释 + 空行占 >90%）
- 迁移或重构后需要清理冗余配置
- 准备切换配置方式（如从 env 引用改为直接写入 config.yaml）

## 流程

### 1. 备份

```bash
python3 -c "
import shutil, datetime
backup = '/root/.hermes/.env.backup.' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy('/root/.hermes/.env', backup)
print('Backup:', backup)
"
```

### 2. 统计清理前后对比

```python
with open('/root/.hermes/.env') as f:
    lines = f.readlines()

total = len(lines)
comments = sum(1 for l in lines if l.strip().startswith('#'))
empty = sum(1 for l in lines if l.strip() == '')
active = total - comments - empty

print(f'Total: {total}, Comments: {comments}, Empty: {empty}, Active: {active}')
```

### 3. 提取活跃变量（保留行结构）

```python
with open('/root/.hermes/.env') as f:
    lines = f.readlines()

active = []
for line in lines:
    stripped = line.strip()
    if stripped and not stripped.startswith('#'):
        active.append(line)

with open('/root/.hermes/.env', 'w') as f:
    f.writelines(active)

print(f'Cleaned: {len(lines)} → {len(active)} lines')
```

### 4. 验证

```bash
# 统计行数
wc -l /root/.hermes/.env

# 确认所有活跃变量都在（抽查关键变量）
grep "API_KEY\|TOKEN\|SECRET" /root/.hermes/.env

# 确认备份可用
head -3 /root/.hermes/.env.backup.*
```

## 原则

| 保留 | 删除 |
|------|------|
| `KEY=value` 有效赋值行 | `#` 开头的注释行 |
| `export KEY=value` 格式 | 空行 |
| 变量引用行（KEYS 数组等） | 注释占位符（`# KEY=your_key_here`） |

## 已知陷阱

- ❌ `.env` 中注释的 API Key 占位符**不是**环境变量 — 删了不影响任何功能
- ❌ 不要用 `sed -i` 批量删除，容易误删活跃变量
- ✅ 用 Python 逐行判断最安全
- ⚠️ 清理后检查所有引用该 `.env` 的进程是否需要重启
