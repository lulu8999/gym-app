---
name: docx-automation
title: Word 文档自动化工具集
description: 基于 Markdown + Pandoc 的 Word 文档生成与编辑工具，解决 AI 生成 Word 时表格被拆散、格式混乱的问题
category: productivity
trigger: 用户需要生成 Word 文档、修改 Word 格式、处理表格结构
dependencies: [pandoc, python-docx]
---

# Word 文档自动化工具集

基于 "Markdown 中间格式 + Pandoc 转换" 的可靠 Word 文档生成方案，解决 python-docx 直接操作 Word 时常见的格式问题。

## 核心问题

AI 直接操作 Word 文档时，表格内容很容易被拆散成独立段落：
```
【调节方式】   ← 表头
【特点】       ← 表头
【神经调节】   ← 数据行被拆成3个段落
【快准短】     ← 数据行被拆成3个段落
【膝跳反射】   ← 数据行被拆成3个段落
```

本工具通过 **Markdown 中间格式 + Pandoc 转换** 解决此问题：
```
AI 生成 Markdown → Pandoc 转换 → 标准 Word 文档（表格完整）
```

## 技术原理

**为什么使用 Markdown + Pandoc 而非直接操作 Word？**

AI 直接操作 Word 时常见问题：表格内容被拆散成独立段落，导致 500+ 段落、阅读困难、格式混乱。

解决方案：**Markdown 中间格式 + Pandoc 专业转换**
- AI 只负责生成标准 Markdown
- Pandoc 专业处理格式转换
- 生成的 Word 表格完整、段落数合理

详见：`references/why-markdown-pandoc-works.md`

## 安装依赖

```bash
# 1. 安装 Pandoc
dnf install -y pandoc  # CentOS/RHEL/Fedora
# 或
apt-get install -y pandoc  # Debian/Ubuntu

# 2. 安装 Python 库
pip install python-docx python-pptx openpyxl
```

## 工具脚本

位于 `scripts/` 目录：

- `md_to_office.py` - **主要工具**，支持 Markdown 转 Word/PPT/Excel
- `md_to_docx.py` - Markdown 转 Word 专用工具
- `docx_utils.py` - Word 文档分析与修复工具

## 使用方案

### 方案 1：生成 Word 文档（推荐）

**步骤**：
1. AI 输出标准 Markdown 格式
2. 调用 `md_to_office.md_to_docx()` 转换
3. 得到格式正确的 Word 文档

**示例**：
```python
from scripts.md_to_office import md_to_docx, validate_docx

markdown_content = """
# 第1章 绪论（1分）

## 一、内环和外环

- **内环**：细胞外液，即组织液
- **外环**：整个机体的外界环境

## 三、调节方式

| 调节方式 | 特点 | 例子 |
|---------|------|------|
| 神经调节 | 快准短 | 膝跳反射 |
| 体液调节 | 慢久弥散 | 生长发育 |

> **口诀**：神经快准短，体液慢久宽
"""

# 生成 Word 文档
output = md_to_docx(
    content=markdown_content,
    output_path='/root/output.docx',
    title='306生理学考研资料',
    toc=True
)

# 验证结果
result = validate_docx(output)
print(f"段落数: {result['paragraphs']}")  # 正常数量
print(f"表格数: {result['tables']}")      # 正确识别为1个表格
```

### 方案 2：生成 PPT 演示文稿

**格式约定**：
- `# 标题` → 新幻灯片标题
- `## 副标题` → 幻灯片内容标题
- `- 列表` → 幻灯片正文
- `> 引用` → 重点提示

**示例**：
```python
from scripts.md_to_office import md_to_pptx

ppt_content = """
# 生理学考研重点

## 第1章 绪论
- 内环与外环的区别
- 神经调节 vs 体液调节
- 负反馈与正反馈

> 口诀：神经快准短，体液慢久宽

## 第2章 细胞的基本功能
- 跨膜转运：纯拖散、易化扩散、主动转运
- 信号转导：离子通道、G蛋白偶联受体
- 生物电现象
"""

output = md_to_pptx(
    content=ppt_content,
    output_path='/root/output.pptx',
    title='306生理学考研重点',
    subtitle='2027年考研备考'
)
```

### 方案 3：生成 Excel 表格

**适用场景**：知识点对比表、考点汇总、复习进度跟踪

**示例**：
```python
from scripts.md_to_office import md_to_excel

excel_content = """
# 生理学章节分值统计

| 章节 | 分值 | 重要程度 | 复习状态 |
|------|------|---------|---------|
| 第1章 绪论 | 1分 | 了解 | 完成 |
| 第2章 细胞功能 | 6分 | 重点 | 进行中 |
| 第4章 血液循环 | 8分 | 重中之重 | 未开始 |

# 调节方式对比

| 调节方式 | 特点 | 例子 | 口诀 |
|---------|------|------|------|
| 神经调节 | 快、准、短 | 膝跳反射 | 神经快准短 |
| 体液调节 | 慢、久、弥散 | 生长发育 | 体液慢久宽 |
"""

output = md_to_excel(
    content=excel_content,
    output_path='/root/output.xlsx',
    sheet_name='考研资料'
)
# 会生成2个工作表，每个表格一个
```

### 方案 4：修复现有问题文档

**步骤**：
1. 使用 `docx_utils.py` 分析现有文档
2. 识别问题区域（被拆散的表格）
3. 重新生成 Markdown 并转换

**示例**：
```python
from scripts.docx_utils import analyze_docx_structure, find_table_like_regions

# 分析问题
stats = analyze_docx_structure('problem.docx')
print(f"短段落数: {stats['short_paragraphs']}")  # 如果很多，说明表格被拆散

# 查找可能的表格区域
regions = find_table_like_regions('problem.docx')
print(f"发现 {len(regions)} 个可能的表格区域")
```

### 方案 3：清理空段落

```python
from scripts.docx_utils import clean_empty_paragraphs

# 清理文档中的空段落
clean_empty_paragraphs(
    docx_path='input.docx',
    output_path='cleaned.docx'
)
```

## Markdown 格式规范

为了获得最佳转换效果，请遵循以下规范：

### 标题
```markdown
# 第1章 绪论（1分）      → 一级标题
## 一、内环和外环      → 二级标题
### 1. 神经调节            → 三级标题
```

### 列表
```markdown
- 项目一
- 项目二
  - 子项目    → 支持嵌套
```

### 表格
```markdown
| 标题1 | 标题2 | 标题3 |
|-------|-------|-------|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |
```

### 引用/口诀
```markdown
> **口诀**：神经快准短，体液慢久宽

> **易错点**：请注意 xxx
```

### 重点标记
```markdown
- **重点**：这是重要内容
- ***必考***：这是必考内容
```

## 协作工作流（与 Claude Code）

对于复杂文档任务，采用**分工协作**模式：

| 角色 | 职责 |
|------|------|
| **Claude Code** (子代理) | 生成完整 Markdown 内容、编写转换代码 |
| **我** (主代理) | 协调、调用工具转换、验证结果、汇报 |

**标准流程**：
```
1. 我接收任务
2. 我分析需求，制定 Markdown 结构方案
3. Claude Code 按方案生成完整 Markdown 内容
4. Claude Code 编写/优化转换代码（如需要）
5. 我调用 md_to_office 工具进行转换
6. 我验证输出质量并汇报
```

详见：`references/claude-coordination.md`

## 用户偏好与工作流

### 自动化原则
- 用户强调："创建自动化流程，而不是每次重新写"
- 所有文档生成任务必须走此工具流程
- 禁止直接用 `python-docx` 操作 Word 内容

### 格式要求
- 表格必须保持完整（不能拆散成段落）
- 删除多余空行
- 不同部分只需换行，不需要空行分隔

### 工作流程
1. 用户提供内容或要求
2. AI 生成标准 Markdown
3. 调用 `md_to_office.convert_md()` 转换
4. 验证输出质量
5. 交付结果

### 服务器资源参考
- CPU: 4核
- 内存: 3.6GB (可用 2.1GB)
- 建议并行任务: 最多 4-6 个

## 命令行使用

```bash
# Markdown 转 Word
python scripts/md_to_office.py docx input.md output.docx

# Markdown 转 PPT
python scripts/md_to_office.py pptx input.md output.pptx

# Markdown 转 Excel（自动提取表格）
python scripts/md_to_office.py xlsx input.md output.xlsx

# 分析文档结构
python scripts/docx_utils.py analyze document.docx

# 清理空段落
python scripts/docx_utils.py clean input.docx [output.docx]

# 提取表格
python scripts/docx_utils.py extract document.docx
```

## API 参考

### md_to_office.convert_md()

统一入口函数，支持所有格式：

```python
from scripts.md_to_office import convert_md

# 转换为 Word
convert_md(content, 'output.docx', format='docx', title='标题', toc=True)

# 转换为 PPT
convert_md(content, 'output.pptx', format='pptx', title='标题', subtitle='副标题')

# 转换为 Excel
convert_md(content, 'output.xlsx', format='xlsx', sheet_name='Sheet1')
```

## 注意事项

1. **始终保留原始文件** - 转换前备份原始文档
2. **验证结果** - 转换后使用 `validate_docx()` 检查
3. **表格行数** - 正常文档应该有少量段落（每个表格只占1段）
4. **中文字体** - 确保系统安装了中文字体

## 高级用法：合并多个已有 Word 文档

### 问题场景
当需要将多个已有的 Word 文档按顺序合并为一个完整文档时，**保留原始格式**是关键要求。常见方法有缺陷。

### 方法对比

| 方法 | 保留格式 | 表格网格线 | 页眉页脚 | 适用场景 |
|------|---------|-----------|---------|---------|
| python-docx 逐段复制 | ❌ 全部丢失 | ❌ | ❌ | ❌ 严禁使用 |
| Pandoc 合并 | ⚠️ 部分保留 | ❌ 丢失 | ❌ | 格式要求不高的场景 |
| XML 元素直接复制 | ✅ 完整保留 | ✅ 保留 | ❌ | **格式要求严格但不需页眉页脚** |
| **Word→PDF→合并** | ✅ 100%保留 | ✅ 保留 | ✅ 保留 | **毕业论文装订推荐** |
| Mac WPS 合并 | ✅ 100%保留 | ✅ 保留 | ✅ 保留 | 最可靠但需要 Mac |

> ⚠️ **毕业论文装订必须用 XML 元素复制法**！Pandoc 会丢失表格网格线、内容挤在一起。

### 方法 1：XML 元素直接复制（推荐用于毕业论文）

```python
from docx import Document

# 按装订顺序读取源文件
files = [
    "封面.docx",
    "独创性声明.docx",
    "任务书.docx",
    "开题报告.docx",
    "论文正文.docx",
    "评阅教师评分.docx",
    "成绩评定表.docx",
]

output = Document()

for file in files:
    src = Document(file)
    
    # 直接复制整个 element body 到输出文档
    # 这种方式完整保留原始格式（字体、字号、表格样式、分页等）
    for element in src.element.body:
        output.element.body.append(element)
    
    # 每个文档后分页
    output.add_page_break()

output.save("最终归档材料.docx")
```

**优点**：
- 完整保留原始格式（字体、字号、段落样式）
- 表格的网格线、边框样式完全保留
- 分页符自然保留
- 简单可靠

**适用场景**：
- 毕业论文装订（格式要求严格）
- 正式文档合并
- 需要保留原始表格样式的场景

### 方法 2：Pandoc 合并（仅格式要求不高时使用）

```bash
# 按顺序合并
pandoc 01_封面.docx 02_任务书.docx 03_论文正文.docx -o merged.docx
```

**问题**：
- ⚠️ 表格的边框/网格线会丢失
- ⚠️ 部分段落样式可能错乱
- 适用于格式要求不高的场景

### 常见错误（不要这样做）

❌ 用 python-docx 逐个复制段落：
```python
# 这种方式会丢失原始格式！
for para in doc1.paragraphs:
    new_doc.add_paragraph(para.text)  # 只复制文字，格式全丢
```

❌ 用 Pandoc 合并毕业论文/正式文档：
```bash
# 会丢失表格网格线、内容挤在一起！
pandoc doc1.docx doc2.docx -o merged.docx
```

❌ 忽略源文件内容重叠问题：
```python
# 假设最终稿_稿件.docx 已经包含封面+独创性声明+正文
# 如果前面已经加了封面.docx和独创性声明.docx
# 就会导致内容重复！
files = [
    "封面.docx",  # 内容1
    "独创性声明.docx",  # 内容2
    "最终稿_稿件.docx",  # 包含了内容1+2+正文！会重复！
]
```

### 常见问题汇总（来自用户反馈）

| 问题现象 | 原因 | 解决方案 |
|---------|------|---------|
| 格式全错 | 用 python-docx 逐段复制 | 用 XML 元素直接复制法 |
| 表格网格线丢失 | Pandoc 合并或逐段复制 | 用 XML 元素直接复制法 |
| 不同文档内容挤在一起 | 没有在文档之间添加分页 | 每份文档后加 `add_page_break()` |
| 页眉页脚丢失 | python-docx 读不出 header/footer | 用 Mac WPS 合并，或手动复制 |
| 小标题/目录标题错乱 | 源文件内容重叠未检查 | 先分析源文件内容范围，去重 |
| 封面出现2次 | 源文件本身包含封面 | 只取需要的部分，不要重复 |

### 用户工作流偏好（重要）

1. **先研究再动手**：用户明确要求"先去寻找网上处理文档的案例和相关技能跟插件，然后再做"
2. **不要照抄模板**：按一般毕业论文装订顺序即可，不用完全复制模板的排法
3. **格式要求严格**：毕业论文装订必须保留所有原始格式（字体、字号、表格线、页眉页脚）
4. **优先使用 Mac WPS**：当页眉页脚必须保留时，优先使用 Mac 上的 WPS 图形界面合并

**问题场景**：用户的「最终稿_稿件.docx」实际上包含了完整内容：
- 封面（学生信息）
- 独创性声明与版权使用授权书
- 论文正文（摘要、Abstract、目录、正文、致谢、参考文献）

如果直接按顺序合并，会导致：
- 封面出现 2 次
- 独创性声明出现 2 次
- 论文正文内容完全重复

**正确的处理方式**：
1. 先单独检查每个源文件包含哪些部分
2. 明确只需要「最终稿_稿件.docx」的**正文部分**（从摘要开始，到参考文献结束）
3. 前面只加：封面 → 独创性声明 → 任务书 → 开题报告 → 指导记录表 → 评阅 → 答辩 → 成绩评定

**验证方法**：合并后检查关键标题是否出现 2 次以上
```python
doc = Document("最终归档材料.docx")

# 统计每个关键标题出现的次数
from collections import Counter
title_counts = Counter()
key_titles = ["本科毕业", "独创性声明", "版权", "任务书", "开题报告", 
              "指导记录", "摘  要", "ABSTRACT", "致谢", "参考文献", "评阅", "成绩评定"]

for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    for t in key_titles:
        if t in text:
            title_counts[t] += 1

print(title_counts)
# 输出类似：{'本科毕业': 2, '独创性声明': 2, ...} 
# 如果某个标题出现2次，说明存在重复，需要修复
```

**经验总结**：
- 毕业论文的「最终稿」通常包含完整内容（封面+声明+正文）
- 装订时只需要取正交部分，前面加独立的各种表格
- 合并后务必验证关键标题位置

✅ 用 XML 元素直接复制（保留原始格式）

### 实际案例：毕业论文装订

**问题场景**：合并多个毕业论文材料文档时，发现以下问题：
- 封面重复出现
- 论文正文内容重复（摘要、目录、正文出现了两次）
- 任务书、开题报告、指导记录表可能缺失

**原因**：源文件之间存在内容重叠，例如「最终稿_稿件.docx」可能已包含封面、独创性声明等部分。

**解决方案**：
1. 先单独检查每个源文件的内容范围
2. 明确每个文件需要提取的部分（如：封面.docx 只需学生信息表格，论文正文.docx 只需正文部分）
3. 合并后验证关键标题位置，检查是否有重复

**验证脚本**：
```python
from docx import Document

doc = Document("最终归档材料.docx")

# 检查关键标题位置
key_titles = ["本科毕业", "独创性声明", "任务书", "开题报告", 
              "指导记录", "摘  要", "致谢", "参考文献", "评阅", "成绩评定"]

for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    for t in key_titles:
        if t in text and len(text) < 30:
            print(f"P{i}: {text[:35]}")

# 检查是否有重复（同一标题出现多次）
# 如果同一关键标题出现2次以上，说明存在重复内容
```

**推荐流程**：
1. 分析每个源文件的内容范围
2. 用 delegation 委托给 Claude Code 执行 XML 级别复制
3. 合并后用脚本验证结构
4. 发现重复则删除重复部分

## 毕业论文装订特别提示

### 常见问题（已有人踩坑）
- **表格网格线消失** → 使用了 Pandoc 合并
- **不同文档内容挤在一起** → 没有在文档之间添加分页
- **字体/字号变了** → 用 python-docx 逐段复制
- **页眉页脚丢失** → python-docx 技术限制，无法读取 header/footer
- **封面/内容重复出现** → 源文件本身包含多部分，未检查内容重叠

### 正确流程
```python
from docx import Document

# ⚠️ 重要：先检查每个源文件包含哪些部分！
files = ["封面.docx", "独创性声明.docx", "任务书.docx", "开题报告.docx", 
         "指导记录表.docx", "论文正文.docx", "评阅教师评分.docx", 
         "答辩组评分.docx", "成绩评定表.docx"]

# 合并前先分析每个文件
for f in files:
    doc = Document(f)
    print(f"\n=== {f} ===")
    key_titles = ["本科", "独创", "版权", "任务书", "开题", "指导", "摘  要", "致谢", "参考文献"]
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        for t in key_titles:
            if t in text and len(text) < 30:
                print(f"  P{i}: {text[:35]}")

# 检查是否有重复（同一标题出现2次以上说明有问题）
```

output = Document()
for f in files:
    src = Document(f)
    for element in src.element.body:
        output.element.body.append(element)
    output.add_page_break()  # 每份文档后分页

output.save("最终归档材料.docx")
```

## 故障排除

### 表格转换不正确
- 确保 Markdown 表格语法正确（有分隔行 |---|---|）
- 检查是否有多余空格

### 中文乱码
```bash
# 安装中文字体
dnf install -y fonts-noto-cjk fonts-wqy-microhei
```

### Pandoc 未找到
```bash
# 检查安装
which pandoc
pandoc --version
```

## 相关参考文档

- `references/word-merge-tool-research.md` - Word 文档合并工具调研（测试了哪些工具、为什么失败）
- `references/why-markdown-pandoc-works.md` - 为什么 Markdown+Pandoc 方案可行
- `references/claude-coordination.md` - 与 Claude Code 协作流程

## 重要限制：页眉页脚无法保留

### 问题描述
python-docx 库存在一个技术限制：**只能读写段落和表格，无法读取/写入页眉页脚**。

当使用 XML 元素复制法合并文档时，页眉页脚（header/footer）会丢失，因为它们不属于 `document.body`，而是属于 `section` 级别的 `hdr`/`ftr` 元素。

### 受影响场景
- 毕业论文装订（论文正文通常有页眉页脚）
- 正式文档合并（需要保留原始页眉页脚）
- 带有章节标题的文档

### 解决方案

#### 方案 0：Word 转 PDF 再合并（推荐用于毕业论文）⚡

**核心思想**：先把每个 Word 转成 PDF（完美保留格式），再用 pdfunite 合并 PDF。

**优点**：
- ✅ 100% 保留页眉页脚、页码、水印等所有元素
- ✅ 表格网格线完美保留
- ✅ 分页自然保留
- ✅ 简单可靠，成功率 100%

**操作步骤**：
```bash
# 1. 用 LibreOffice 将 docx 转成 pdf
libreoffice --headless --convert-to pdf 封面.docx --outdir pdf/
libreoffice --headless --convert-to pdf 独创性声明.docx --outdir pdf/
# ... 依次转换所有文档

# 2. 用 pdfunite 合并 PDF（按装订顺序）
pdfunite 封面.pdf 独创性声明.pdf 论文正文.pdf 成绩评定表.pdf 任务书.pdf 开题报告.pdf 指导记录表.pdf 评阅教师评分.pdf 答辩组评分.pdf 最终归档材料.pdf
```

**实际案例（2025-06-10）：**
用户需要合并9个毕业论文材料文档，按指定顺序：封面 → 独创声明 → 最终稿 → 成绩评定表 → 任务书 → 开题报告 → 指导记录表 → 评阅教师评分 → 答辩组评分。

问题：最终稿.docx 包含完整内容（封面+独创声明+正文），直接合并会导致重复。

**教训**：合并前必须先检查每个源文件包含哪些部分！常见情况：
- 封面.docx 可能包含"材料目录"（需要去掉）
- 最终稿_稿件.docx 通常包含完整内容（封面+声明+正文）

解决：
1. 先单独转换每个 docx 为 PDF（`libreoffice --headless --convert-to pdf`）
2. **只取最终稿的正文部分**（去掉重复的封面+独创声明）
3. 按顺序用 pdfunite 合并

成功保留所有格式，包括页眉页脚！

**验证结果**：
- PDF 大小：1.7-1.9MB
- 所有格式完整保留
- 分页正确

**重要教训**：
- WPS Linux 无法在 VPS（OpenCloudOS/RHEL）上安装 —— 没有 RPM 包，deb 包无法转换
- Mac 下载大型文件需要开代理（Shadowrocket 是 iOS 软件，Mac 需要 ClashX/Surge 等）
- 遇到下载卡住先检查网络，别反复尝试

**完整脚本**：
```bash
# 转换所有 docx 为 pdf
cd /root/doc_merge_temp
mkdir -p pdf

for f in *.docx; do
    soffice --headless --convert-to pdf "$f" --outdir pdf/
done

# 按顺序合并（顺序由用户提供）
cd pdf
pdfunite 01_封面.pdf 02_独创性声明.pdf 06_论文正文.pdf 09_成绩评定表.pdf \
    03_任务书.pdf 04_开题报告.pdf 05_指导记录表.pdf 07_评阅教师评分.pdf \
    08_答辩组评分.pdf "/root/223405415 陆海天.pdf"
```

**验证**：检查 PDF 页数
```bash
pdfinfo 最终归档材料.pdf | grep Pages
# 应该是各部分页数之和
```

#### 方案 X：逐个转换后分别发送（用户想检查每个部分）

如果用户想逐个检查每个部分，可以：
1. 把每个 docx 分别转成 PDF
2. 按顺序逐个发给他检查
3. 确认无误后再用 pdfunite 合并

```bash
# 转换所有 docx 为 pdf
cd /root/doc_merge_temp
mkdir -p pdf

for f in *.docx; do
    soffice --headless --convert-to pdf "$f" --outdir pdf/
done

# 分别发送 pdf/01_封面.pdf, pdf/02_独创性声明.pdf 等给用户
```

**适用场景**：用户需要逐个确认每个部分的格式是否正确

**适用场景**：
- 毕业论文装订（格式要求严格）
- 需要 100% 保留页眉页脚
- 最终交付格式可以是 PDF（如果必须是 Word，见方案 1 或 2）

#### 方案 1：使用 Mac 上的 WPS 合并（推荐）
Mac 上有 WPS（在外接 SSD 里），可以直接图形界面合并，操作步骤：
1. 打开 WPS，路径可能是：
   - `/Volumes/ssd/Applications/wpsoffice.app`（SSD 里）
   - `/Applications/wpsoffice.app`（本地 Applications）
2. 新建空白文档
3. 点击「插入」→「从文件导入」→「页面」
4. 按顺序逐个插入各部分文档
5. 保持原始格式（包括页眉页脚）
6. 保存

**VPS SSH 到 Mac 的方法**：
```bash
# 确保 VPS 上有 SSH 密钥
ls ~/.ssh/id_ed25519

# 连接 Mac（用户是 lulu，IP 可能是 100.114.207.6）
ssh -i ~/.ssh/id_ed25519 lulu@100.114.207.6

# 传文件到 Mac
scp -i ~/.ssh/id_ed25519 /root/doc_merge_temp/*.docx lulu@100.114.207.6:~/论文合并/
```

**优势**：完美保留所有格式，包括页眉页脚、页码、表格样式等。

**如何查找 Mac 上的 WPS**：
```bash
# SSH 到 Mac 后
ls /Volumes/           # 查看外接硬盘
ls /Volumes/ssd/Applications/ | grep -i wps  # 查找 WPS
```

#### 方案 2：手动复制页眉页脚
合并后手动操作：
1. 打开合并后的文档
2. 打开原始「论文正文.docx」
3. 复制页眉页脚内容
4. 粘贴到合并文档对应位置

#### 方案 3：使用专门的 Word 合并工具
- Microsoft Word 本身的「比较和合并」功能
- WPS 文字的「合并文档」功能

### 为什么 python-docx 无法处理页眉页脚

Word 文档结构：
```
document.xml
├── body (正文内容)
├── hdr (页眉) ← python-docx 读不到
├── ftr (页脚) ← python-docx 读不到
└── sectPr (页面设置)
```

python-docx 的 `Document` 对象只暴露了 `body`，页眉页脚需要直接操作底层 XML（`element.hdr`, `element.ftr`），但这非常复杂且容易出错。

### 经验总结
- 如果格式要求严格（毕业论文、正式文档），**直接用 Mac/Windows 上的 WPS/Word 合并**
- python-docx/pandoc 合并适用于格式要求不高的场景
- 如果已经用程序合并了，手动复制页眉页脚是最后的补救办法
