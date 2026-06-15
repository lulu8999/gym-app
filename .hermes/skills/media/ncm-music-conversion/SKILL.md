---
name: ncm-music-conversion
title: NCM 音乐批量转换与分类
description: "通过SSH连接Windows，用ncmdump将网易云.ncm文件批量转换为.mp3，按中英文分类去重"
version: 1.0.0
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [Media, Music, NCM, Conversion, Windows]
    category: media
    requires_toolsets: [terminal]

---

# NCM 音乐批量转换与分类

当用户需要将网易云音乐 .ncm 文件转换为 .mp3 并分类整理时使用。

## 前置条件

- Windows 机器可通过 SSH 访问（sshpass + 密码认证）
- Python 已安装（Windows 上，如 `E:\Python\python.exe`）
- ncmdump Python 包已安装（`pip install ncmdump`）

## 工作流程

### 1. 连接 Windows

```bash
sshpass -p '密码' ssh -o StrictHostKeyChecking=no -p 2222 用户名@IP "命令"
```

Lulu 的 Win 笔记本：100.80.251.96:2222，用户陆海天。

### 2. 检查 ncmdump 可用性

```bash
sshpass -p '密码' ssh ... "E:\Python\python.exe -c \"import ncmdump; print('ok')\""
```

未安装则：`E:\Python\python.exe -m pip install ncmdump`

### 3. 批量转换脚本

**关键：** SSH 传中文路径有编码问题，先写脚本到本地 `/tmp/convert_ncm.py`，再用 `scp` 传过去执行。

脚本核心逻辑：
```python
import ncmdump, shutil
from pathlib import Path

src = Path(r'C:\Users\用户名\Desktop\vipmusic')
dst = Path(r'C:\Users\用户名\Desktop\mp3')
dst.mkdir(parents=True, exist_ok=True)

for f in src.glob('*.ncm'):
    out = dst / (f.stem + '.mp3')
    if out.exists():
        continue
    result = ncmdump.dump(str(f))
    if result and Path(result).exists():
        shutil.move(result, str(out))
```

### 4. 分类脚本（中英文）

按歌名是否含中文字符分类：
```python
import re
def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))
```

- 包含中文 → `F:\中文`
- 不包含 → `F:\外文`

### 5. 去重

按歌名去重（提取 "Artist - Title" 中的 Title 部分），保留文件大小较大的那个。

## 常见陷阱

1. **SSH 中文编码** — Windows SSH 的 `dir /b` 输出中文会乱码，但文件操作不受影响
2. **ncmdump.dump() 返回路径** — 返回的是转换后的文件路径，需要手动 move 到目标目录
3. **已有文件跳过** — 转换前检查目标文件是否存在，避免重复转换
4. **超时问题** — 133 个文件转换约需 2-3 分钟，SSH 命令设 300s 超时
5. **分类脚本后台运行** — 文件多时可能超时，用 `start /b` 后台执行
6. **ncmdump 参数** — 用 `ncmdump.dump()` 不是 `ncmdump.decrypt()`

## 参考文件

- `scripts/convert_ncm.py` — 批量转换脚本模板
- `scripts/sort_music.py` — 分类+去重脚本模板
