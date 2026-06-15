---
name: document-editing
title: WPS/Word 文档编辑 — 论文与公文
description: 使用 python-docx 编辑 .docx 文件，支持学术论文润色和党政公文排版
category: productivity
trigger: 用户需要修改论文、公文或其他 .docx 格式文档，涉及文字润色、格式调整、段落重写、文档合并
dependencies: [python-docx]
---

# WPS/Word 文档编辑指南

用于修改 WPS/Word（.docx）格式的学术论文和党政公文。采用 python-docx 库进行程序化编辑。

## 前置检查

```bash
python3 -c "import docx; print(docx.__version__)"
```

如果未安装：`pip install python-docx`

## 文档读取

### 读取全文

```python
from docx import Document
doc = Document('论文.docx')

# 遍历段落
for i, para in enumerate(doc.paragraphs):
    print(f'{i}: [{para.style.name}] {para.text[:100]}')

# 遍历表格
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text)
```

### 读取格式信息

```python
for para in doc.paragraphs:
    fmt = para.paragraph_format
    align = fmt.alignment          # 对齐方式
    space_before = fmt.space_before  # 段前间距
    space_after = fmt.space_after    # 段后间距
    line_spacing = fmt.line_spacing  # 行距
    for run in para.runs:
        font = run.font
        font.name, font.size, font.bold, font.italic
```

## 文字润色（学术论文）

### 逐段替换

```python
from docx import Document

doc = Document('论文.docx')
for para in doc.paragraphs:
    if '旧表述' in para.text:
        # 保留格式替换
        for run in para.runs:
            if '旧表述' in run.text:
                run.text = run.text.replace('旧表述', '新表述')
doc.save('论文_修改版.docx')
```

### 整段重写

```python
# 找到目标段落索引
target_idx = None
for i, para in enumerate(doc.paragraphs):
    if '待重写的段落开头' in para.text:
        target_idx = i
        break

# 记录旧段落的格式
old_para = doc.paragraphs[target_idx]
old_fmt = {
    'alignment': old_para.paragraph_format.alignment,
    'space_before': old_para.paragraph_format.space_before,
    'space_after': old_para.paragraph_format.space_after,
    'style': old_para.style,
}

# 清空并写入新内容
old_para.clear()
run = old_para.add_run('新段落内容...')
run.font.name = '宋体'
run.font.size = Pt(12)
```

## 排版调整（党政公文）

### 常见党政公文格式

| 要素 | 规范 |
|------|------|
| 标题 | 二号方正小标宋/宋体，居中 |
| 正文 | 三号仿宋，首行缩进2字符 |
| 一级标题 | 三号黑体，序号一、二、三 |
| 二级标题 | 三号楷体，序号（一）（二）（三） |
| 行距 | 固定值 28 磅 |
| 页边距 | 上3.7cm 下3.5cm 左2.8cm 右2.6cm |

### 设置段落格式

```python
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

def format_gongwen_body(para):
    """设置公文正文格式"""
    pf = para.paragraph_format
    pf.first_line_indent = Cm(0.74)  # 首行缩进2字符（三号字约0.74cm）
    pf.line_spacing = Pt(28)          # 固定值28磅
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    for run in para.runs:
        run.font.name = '仿宋'
        run.font.size = Pt(16)        # 三号 = 16pt
```

### 设置页面边距

```python
for section in doc.sections:
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)
```

## Word 文档合并（推荐底层 XML 复制法）

### 重要提示

**不要用逐段复制的方法！** 简单复制段落和 run 会导致格式丢失：
- ❌ 表格网格线丢失
- ❌ 字体格式丢失（尤其是中文）
- ❌ 段落间距丢失
- ❌ 分页符丢失

**正确方法：使用底层 XML 复制（copy.deepcopy）** ✅

### 底层 XML 复制代码

```python
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import copy
import os

def merge_docs_xml_deepcopy(input_files, output_path):
    """
    使用底层 XML deep copy 合并 Word 文档
    完整保留：字体、字号、表格网格线、段落间距、分页、图片
    """
    output = Document()
    output._body.clear()
    
    for idx, (name, src_path) in enumerate(input_files):
        if not os.path.exists(src_path):
            print(f"❌ {name} 不存在: {src_path}")
            continue
            
        print(f"✅ 处理: {name}")
        src_doc = Document(src_path)
        
        # 获取源文档的 body 元素，深拷贝所有子元素
        src_body = src_doc._body._element
        for child in list(src_body):
            new_child = copy.deepcopy(child)
            output._body._element.append(new_child)
        
        # 添加分页符（除最后一个文档外）
        if idx < len(input_files) - 1:
            p = OxmlElement('w:p')
            r = OxmlElement('w:r')
            br = OxmlElement('w:br')
            br.set(qn('w:type'), 'page')
            r.append(br)
            p.append(r)
            output._body._element.append(p)
    
    # 使用最后一个文档的页面设置
    if src_doc.sections:
        output.sections[0]._sectPr = copy.deepcopy(src_doc.sections[-1]._sectPr)
    
    output.save(output_path)
    print(f"\n✅ 已保存: {output_path}")

# 使用示例（毕业论文装订顺序）
files = [
    ("封面", "封面.docx"),
    ("独创性声明", "独创性声明与版权使用授权书.docx"),
    ("任务书", "任务书.docx"),
    ("开题报告", "开题报告.docx"),
    ("指导记录表", "指导记录表.docx"),
    ("论文正文", "最终稿_稿件.docx"),
    ("评阅教师评分", "评阅教师评分.docx"),
    ("答辩组评分", "答辩组评分.docx"),
    ("成绩评定表", "成绩评定表.docx"),
]
merge_docs_xml_deepcopy(files, "最终归档材料.docx")
```

### 毕业论文装订标准顺序

1. 封面（只保留学生信息表格，去掉材料目录）
2. 独创性声明与版权使用授权书
3. 任务书
4. 开题报告
5. 指导记录表
6. 论文正文（摘要→Abstract→目录→正文→致谢→参考文献）
7. 评阅教师评分
8. 答辩组评分
9. 成绩评定表

### ⚠️ 重要限制：页眉页脚无法保留

**python-docx 的技术限制**：它只能读取和操作**段落**和**表格**，无法读取 Word 文档中的**页眉**和**页脚**元素。这是 python-docx 库的架构限制，不是代码问题。

**表现**：合并后的文档会丢失：
- 页眉内容（如章节标题）
- 页脚内容（如页码）
- 页面边框/水印
- 分节符设置的页眉页脚不同

**解决方案**：

| 方案 | 做法 | 适用场景 |
|-----|------|---------|
| **方案A：PDF 转换法** ✅ | 每个 docx 转 PDF → 用 pdfunite 合并 | **推荐**，100% 保留所有格式 |
| **方案B：Mac 上用 WPS** | 在 Mac 上手动用 WPS 合并 | 需要图形界面，100% 保留 |
| **方案C：手动复制** | 合并后再手动复制页眉页脚 | 紧急情况，简单文档 |

**方案A 详细步骤（推荐）**：

```bash
# 1. 用 LibreOffice 把每个 docx 转 PDF（保留格式最好）
for f in *.docx; do
    libreoffice --headless --convert-to pdf "$f" --outdir ./pdf/
done

# 2. 按顺序合并 PDF
pdfunite 01_封面.pdf 02_独创性声明.pdf 03_任务书.pdf ... output.pdf
```

**为什么 PDF 能保留而 Word 不能**：
- PDF 是"固化"的最终格式，转换时一次性把所有内容（页眉页脚、页面布局、水印等）全部渲染成图像+文字，100% 保留原貌
- Word 是"源文件"格式，内部是 XML 结构。转换工具读取时只能解析出"段落+表格"，页眉页脚属于另一个独立的 XML 分支（header/footer），python-docx 读不出来

**方案A 的优势**：
- ✅ 100% 保留页眉页脚、页面布局、水印
- ✅ 字体完全不丢失
- ✅ 表格格式完美保留

**详细参考**：

完整代码和常见问题：参阅 `references/word-merge-preserve-format.md`

---

## 常见操作模式

### 模式1：指定段落精确修改

用户说"第三段改一下"时，通过逐段比对定位：

```python
target_text = "用户提到的某个关键词"
for i, para in enumerate(doc.paragraphs):
    if target_text in para.text:
        # 在此修改
        break
```

### 模式2：全文替换

```python
for para in doc.paragraphs:
    for run in para.runs:
        run.text = run.text.replace('旧词', '新词')
```

### 模式3：批量调整格式

```python
from docx.shared import Pt

for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        # 标题不改字体
        continue
    for run in para.runs:
        run.font.size = Pt(14)  # 统一改字号
```

## 保存与输出

```python
# 保存为新文件（不覆盖原稿）
doc.save('论文_修改版.docx')

# 确认保存成功
import os
print(f'文件已保存: {os.path.abspath("论文_修改版.docx")}')
```

## 中文文档生成（PDF/Excel/PPT）

当需要生成PDF、Excel、PPT等格式，或遇到"中文乱码"问题时，使用完整的`doc_tools`解决方案。

### 快速使用

```python
from doc_tools import create_simple_pdf, create_simple_excel, create_simple_ppt

# 生成PDF - 支持中文、数学符号、特殊符号
create_simple_pdf('output.pdf', '标题', '中文内容αβγ')

# 生成Excel - 支持格式化表格
create_simple_excel('output.xlsx', 
    data=[['张三', 85], ['李四', 92]],
    headers=['姓名', '分数'],
    title='成绩单'
)

# 生成PPT - 支持多张幻灯片
create_simple_ppt('output.pptx', '考研复习', [
    ('第一章', '细胞的基本功能'),
    ('第二章', '神经传导'),
])
```

### 完整实现

完整工具包代码：参阅 `references/chinese-doc-tools.md`

```bash
# 安装依赖
python3 -m pip install fpdf2 reportlab openpyxl xlsxwriter python-pptx pymupdf
```

### 字符支持范围

| 类型 | 支持内容 |
|------|------|
| 中文 | 简体/繁体、生偏字 |
| 标点 | ，。！？；：（）【】《》「」"”""'' |
| 数学 | αβγδ∑√∞≤≥≠≈±×÷°′″℃Ω |
| 符号 | ©®™°…——●★☆○◆• |
| 箭头 | ←↑→↓↔↕⇐⇑⇒⇓ |
| 货币 | ￥¥$\u20ac£¢ |

## 注意事项

- **始终保存为新文件**，不要覆盖原稿，除非用户明确要求
- **段落格式 vs 字符格式**：`paragraph_format` 控制段整体（对齐、间距），`run.font` 控制具体文字（字体、字号、加粗）
- **一个段落可能有多个 runs**：WPS/Word 在保存时会把一个段落拆成多个 run，替换文字时需要遍历所有 runs
- **表格处理**：表格内容的读取方式不同，用 `doc.tables[i].rows[j].cells[k].paragraphs`
- **图片**：python-docx 对图片支持有限，如需插入/替换图片可用 `add_picture()`
- **大小写/样式名**：不同语言版 Word 的样式名不同（中文版是"正文"、"标题1"，英文版是"Normal"、"Heading 1"）
- **修改前先展示段落概要给用户确认**，避免大范围修改后方向不对

## PDF to Word 转换

将PDF转换为Word格式，保留完整结构、表格和格式。

**完整工作流程**: 参阅 `references/pdf-to-word-conversion.md`

关键原则：
1. **先提取全部内容**，验证完整性后再报告
2. **必须包含目录页** - 用户期望的章节导航
3. **表格转为真正的Word表格** - 不是文本表示
4. **分值符号统一为~** - 如 `5~8分` 而非 `5-8分`
5. **封面+目录+正文+结语** 完整结构

```python
from docx import Document
import fitz

# 1. 完整提取
doc_pdf = fitz.open('input.pdf')
all_text = '\n'.join([doc_pdf[i].get_text() for i in range(len(doc_pdf))])
doc_pdf.close()

# 2. 识别章节并生成结构化Word文档
# ... (详见 references/pdf-to-word-conversion.md)
```

## PDF内容修改与校对

当需要修改现有PDF内容（如更正文字、添加页面）时，使用PyMuPDF提取和重新生成。

### 提取PDF内容

```python
import fitz  # PyMuPDF

# 打开PDF
doc = fitz.open('input.pdf')

# 提取所有页面文本
all_text = []
for page in doc:
    all_text.append(page.get_text())

doc.close()

# 处理内容
full_text = '\n'.join(all_text)
```

### 修改内容并重新生成

```python
import fitz
from doc_tools.pdf_generator import PDFGenerator

# 1. 读取原PDF
doc = fitz.open('input.pdf')
pages_text = [page.get_text() for page in doc]
doc.close()

# 2. 修改内容
modified = []
for text in pages_text:
    text = text.replace('旧文字', '新文字')
    modified.append(text)

# 3. 重新生成PDF
content = {
    'title': '标题',
    'sections': [{'heading': '', 'body': '\n'.join(modified)}]
}
generator = PDFGenerator(engine='reportlab')
generator.create_document('output.pdf', content)
```

### 校对检查清单

修改PDF前应检查以下项目：

| 检查项 | 说明 |
|--------|------|
| 中文显示 | 确认无乱码、无替换字符(�) |
| 章节顺序 | 确认章节按逻辑顺序排列 |
| 分值符号 | 统一使用～而非- (5~8分而非5-8分) |
| 标点格式 | 统一全角标点 |
| 重点标记 | 必考/重点内容应有明确标识 |
| 表格格式 | 对比表应结构清晰，避免多余符号 |
| 多余内容 | 删除页尾多余符号(如•••) |

## 常见陷阱

### 段落格式陷阱（用户反馈修正）

**问题**：章节之间空行过多、表格内容被拆成独立段落、短句被不必要地换行

**表现**：
```
段落36: 【三、调节方式】
段落37: 【调节方式】  ← 这应是表格单元格
段落38: 【特点】      ← 被拆成独立段落
段落39: 【例子】      ← 原本是一行表格内容
段落40: 【神经调节】  ← 数据行被拆散
段落41: 【快、准、短】
段落42: 【膝跳反射...】
```

**根本原因**：
1. 从PDF提取时表格结构未正确识别
2. 生成Word时未使用 Table 对象，而是用段落模拟表格
3. 章节之间插入了多余的空段落

**解决方案**：
1. **章节间距**：章节之间只保留1个空行（或不保留），不要用多个空段落
2. **表格重建**：将连续短段落识别为表格，用 `doc.add_table()` 重建真正的表格结构
3. **段落合并**：同一知识点的内容应合并为完整段落，不要按句子拆分

**检查清单（生成后必须检查）**：
```python
# 1. 检查空行数量
empty_count = sum(1 for p in doc.paragraphs if not p.text.strip())
print(f"空行数量: {empty_count}")  # 应控制在合理范围

# 2. 检查是否有表格内容被拆段
short_paras = [(i, p.text) for i, p in enumerate(doc.paragraphs) 
               if 0 < len(p.text.strip()) < 20]
if len(short_paras) > 50:  # 短段落过多，可能有表格被拆分
    print("警告：检测到大量短段落，可能有表格内容被错误拆分")
```

### 中文字体乱码

**问题现象**：生成PDF/Excel/PPT时中文显示为方框或问号。

**根本原因**：库未正确加载中文字体。

**解决方案**：
1. 确保系统已安装中文字体（如 Noto Sans CJK SC）
2. 使用字体管理器自动检测并选择合适的字体
3. **fpdf2 必须使用子集字体**（subset font）而非完整字体文件，否则报错

```python
# 字体回退机制
subset_font = '/usr/share/fonts/chinese/NotoSans_subset.ttf'
if os.path.exists(subset_font):
    pdf.add_font('Chinese', '', subset_font)
else:
    pdf.add_font('Chinese', '', '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf')
```

4. **完整解决方案**：使用`doc_tools`工具包，已经处理好字体回退和兼容性问题。
```python
from doc_tools import create_simple_pdf, create_simple_excel, create_simple_ppt
```
