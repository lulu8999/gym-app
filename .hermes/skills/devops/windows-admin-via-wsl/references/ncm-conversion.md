# ncm → mp3 转换（WSL + Windows 桌面文件）

## 适用场景

网易云音乐下载的 `.ncm` 加密文件需要转换为标准 `.mp3` 格式。文件存于 Windows 桌面，通过 WSL `/mnt/c/` 挂载访问。

## 工具链

### 方案 A：WSL ncmdump 二进制（原方案）

| 工具 | 位置 | 用途 |
|:-----|:-----|:-----|
| `ncmdump` v1.5.1 | `/home/lulu/bin/ncmdump` | 解密 ncm → 原始格式（通常直接输出 mp3） |
| `ffmpeg` | `/usr/bin/ffmpeg` | 备选：当 ncmdump 输出 flac 时转 mp3 |

适用场景：WSL SSH 正常，文件在 `/mnt/c/` 可访问路径。

### 方案 B：Windows Python ncmdump（推荐直连 Windows 时）

```bash
# 安装（只需一次）
sshpass -p '密码' ssh -p 2222 陆海天@<win-ip> "E:\Python\python.exe -m pip install ncmdump"
```

安装后 Python 包含：`ncmdump`、`pycryptodome`、`mutagen`。

适用场景：直接 SSH 到 Windows（2222 端口），无需 WSL 参与。

**批量转换脚本模板：**

```python
import os, sys, shutil
from pathlib import Path

import ncmdump

src = Path(r'C:\Users\陆海天\Desktop\vipmusic')
dst = Path(r'C:\Users\陆海天\Desktop\mp3')
dst.mkdir(parents=True, exist_ok=True)

ncm_files = list(src.glob('*.ncm'))
print(f'Found {len(ncm_files)} ncm files')

success = 0
for i, f in enumerate(ncm_files):
    out_path = dst / (f.stem + '.mp3')
    if out_path.exists():
        print(f'[{i+1}] SKIP (exists): {out_path.name}')
        success += 1
        continue
    try:
        result = ncmdump.dump(str(f))
        if result and os.path.exists(result):
            shutil.move(result, str(out_path))
            print(f'[{i+1}] OK: {out_path.name}')
            success += 1
        else:
            # ncmdump may save alongside source
            expected = f.with_suffix('.mp3')
            if expected.exists():
                shutil.move(str(expected), str(out_path))
                success += 1
            else:
                print(f'[{i+1}] FAIL: {f.name}')
    except Exception as e:
        print(f'[{i+1}] ERROR: {f.name} -> {e}')

print(f'Done! Success: {success}/{len(ncm_files)}')
```

**使用方法：**
1. 本地写脚本 → SCP 到 Windows 桌面
2. `sshpass ... ssh -p 2222 陆海天@<win-ip> "E:\Python\python.exe <脚本路径>"`
3. 完成后删除临时脚本

⚠️ **`ncmdump.dump()` 返回值**：成功时返回转换后的文件路径（字符串），文件保存在源文件同目录。需要 `shutil.move()` 到目标目录。

## 用户约束

| 规则 | 说明 |
|:-----|:------|
| ✅ 输出到独立文件夹 | 默认 `桌面/mp3/`，不混入源文件 |
| ✅ 保留原文件 | 不删 `.ncm` 源文件（不加 `-m` 参数） |
| ✅ 先报告工具状态 | 用户偏好"装完工具先报告等指令"，已装好的直接开干 |
| ✅ 不猜测不伪造 | 转换结果以实际输出为准 |

## 标准工作流

### 1. 确认工具就绪

```bash
# SSH 进 WSL（从 VPS）
sshpass -p '密码' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96 "/home/lulu/bin/ncmdump --version"
sshpass -p '密码' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96 "ffmpeg -version | head -1"
```

### 2. 列出源文件

```bash
WYY="/mnt/c/Users/陆海天/Desktop/wyy"
sshpass -p '密码' ssh lulu@100.80.251.96 "ls '$WYY'/*.ncm | head -5 && echo '...' && ls '$WYY'/*.ncm | wc -l"
```

### 3. 批量转换

```bash
WYY="/mnt/c/Users/陆海天/Desktop/wyy"
MP3="/mnt/c/Users/陆海天/Desktop/mp3"

sshpass -p '密码' ssh lulu@100.80.251.96 "
mkdir -p '$MP3'
/home/lulu/bin/ncmdump -d '$WYY' -o '$MP3'
"
```

**参数说明：**
- `-d <dir>` — 批量处理目录下所有 ncm 文件
- `-o <dir>` — 输出到指定目录
- `-r` — 递归处理子目录（可选）
- `-m` — 转换后删除源文件（**用户偏好不删，别用**）

### 4. ncmdump 输出行为

| 源格式 | ncmdump 输出 | 需二次转换？ |
|:-------|:-------------|:------------|
| ncm 加密的 mp3 | `.mp3` | ❌ 直接可用 |
| ncm 加密的 flac | `.flac` | ✅ 需 ffmpeg 转 mp3 |

**如果输出含 flac：**

```bash
cd '/mnt/c/Users/陆海天/Desktop/mp3'
for f in *.flac; do
  ffmpeg -i "$f" -q:a 2 "${f%.flac}.mp3" -n
  rm "$f"  # 清理中间 flac
done
```

### 5. 验证结果

```bash
sshpass -p '密码' ssh lulu@100.80.251.96 "
MP3='/mnt/c/Users/陆海天/Desktop/mp3'
echo '文件数: \$(ls \"\$MP3\"/*.mp3 2>/dev/null | wc -l)'
echo '总大小: \$(du -sh \"\$MP3\" | cut -f1)'
"
```

## 常见问题

### Q: ncmdump 找不到命令？
A: 路径 `/home/lulu/bin/ncmdump`，确保 SSH 到 lulu 用户。非交互式 SSH 会话需要完整路径。

### Q: SSH 连不上 WSL？
A: WSL 对话框关闭可能导致 SSH 服务不可用。最多 1 次 ping + 1 次 SSH 尝试，全失败 → 告诉用户检查笔记本网络。

### Q: 中文文件名乱码？
A: WSL 的 `/mnt/c/` 能正确显示 Windows 中文文件名，用引号包裹即可。