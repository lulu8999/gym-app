---
name: chinese-document-generation
title: 中文文档生成工具集
description: 一次性配置好中文字体环境，支持PDF/Excel/PPT生成，确保中文、特殊符号、数学符号都能正常显示不乱码
category: productivity
trigger: 用户需要生成PDF/Excel/PPT文档，特别是涉及中文内容，或抱怨过文档乱码问题
dependencies: [fpdf2, reportlab, openpyxl, xlsxwriter, python-pptx, pymupdf]
---

# 中文文档生成工具集

解决文档生成中的乱码问题，一次配置长期可用。支持PDF、Excel、PPT三种格式，确保中文、标点、特殊符号、数学符号都能正常显示。

## 工作流（重要！）

**用户偏好：先报告计划和Token预算，确认后再执行。**

1. 评估需求范围（PDF/Excel/PPT/全套）
2. 制定计划，明确文件结构
3. **报告Token预算**，等待用户确认
4. 用户确认后执行
5. 生成测试文件验证符号显示正常
6. 报告完成情况和实际Token消耗

## 快速开始

### 第一次配置

```bash
# 1. 安装所有必要库
python3 -m pip install fpdf2 reportlab openpyxl xlsxwriter python-pptx pymupdf

# 2. 检查系统字体
fc-list :lang=zh

# 3. 创建doc_tools目录
mkdir -p /root/users-data/FengZaiQiShi/doc_tools
```

### 项目结构

```
doc_tools/
├── __init__.py              # 包入口
├── fonts.py                 # 字体配置中心
├── pdf_generator.py         # PDF生成
├── excel_generator.py       # Excel生成
├── ppt_generator.py         # PPT生成
└── utils.py                 # 通用工具
```

## 核心文件

### 1. fonts.py - 字体配置中心

统一管理中文字体，提供回退机制：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体配置中心 - 确保中文显示正常
"""

import os

# 字体优免级别（按优先顺序尝试）
FONT_PATHS = [
    '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
    '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
]

FONT_NAMES = [
    'Noto Sans CJK SC',
    'Noto Sans SC',
    'Microsoft YaHei',
    'SimHei',
    'SimSun',
    'Arial Unicode MS',
    'DejaVu Sans',
]

def get_available_font_path():
    """获取第一个可用的字体路径"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    return None

def get_font_name():
    """获取推荐的字体名称"""
    return FONT_NAMES[0]

# 符号测试集（用于验证）
TEST_SYMBOLS = {
    'chinese': '中文测试内容，包含简体和繁體字',
    'punctuation': '，。！？；：（）【】《》「」『』‘’“”～·——',
    'special': '©®™°±×÷…●★☆○◆•＊',
    'math': 'αβγδε∑∏√∞≤≥≠≈°′″℃',
    'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕',
    'currency': '￥¥$€£¢',
}

def get_test_content():
    """获取完整测试内容"""
    lines = []
    for category, content in TEST_SYMBOLS.items():
        lines.append(f"[{category}] {content}")
    return '\n'.join(lines)
```

### 2. pdf_generator.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF生成器 - 支持中文和特殊符号
"""

from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

class ChinesePDF(FPDF):
    """自带中文字体支持的PDF类"""
    
    def __init__(self, font_path=None):
        super().__init__()
        if font_path and os.path.exists(font_path):
            self.add_font('Chinese', '', font_path, uni=True)
            self.add_font('Chinese', 'B', font_path, uni=True)
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Chinese', '', 10)
        self.cell(0, 10, '', 0, 1, 'C')
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Chinese', '', 10)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')

def create_pdf_simple(output_path, title, content, font_path=None):
    """快速创建PDF"""
    pdf = ChinesePDF(font_path)
    pdf.add_page()
    
    # 标题
    pdf.set_font('Chinese', 'B', 16)
    pdf.cell(0, 15, title, 0, 1, 'C')
    pdf.ln(5)
    
    # 内容
    pdf.set_font('Chinese', '', 12)
    pdf.multi_cell(0, 8, content)
    
    pdf.output(output_path)
    return output_path
```

### 3. excel_generator.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel生成器 - 支持中文表头和格式化
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

def create_excel(output_path, data, headers=None, title=None, sheet_name="Sheet1"):
    """
    创建中文Excel
    
    参数:
        output_path: 输出路径
        data: 数据列表，每行是一个列表
        headers: 标题行列表（可选）
        title: 文档标题（可选）
        sheet_name: 工作表名称
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    
    # 字体配置
    header_font = Font(name='Noto Sans CJK SC', size=12, bold=True)
    data_font = Font(name='Noto Sans CJK SC', size=11)
    
    current_row = 1
    
    # 添加标题
    if title:
        ws.merge_cells(f'A1:{get_column_letter(len(headers or data[0]))}1')
        title_cell = ws.cell(row=1, column=1, value=title)
        title_cell.font = Font(name='Noto Sans CJK SC', size=14, bold=True)
        title_cell.alignment = Alignment(horizontal='center')
        current_row = 2
    
    # 添加表头
    if headers:
        for col_idx, header in enumerate(headers):
            cell = ws.cell(row=current_row, column=col_idx + 1, value=header)
            cell.font = header_font
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.font = Font(name='Noto Sans CJK SC', size=12, bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal='center')
        current_row += 1
    
    # 填充数据
    for row_idx, row_data in enumerate(data):
        for col_idx, value in enumerate(row_data):
            cell = ws.cell(row=current_row + row_idx, column=col_idx + 1, value=value)
            cell.font = data_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # 自动调整列宽
    for col_idx in range(1, (len(headers) if headers else len(data[0])) + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 15
    
    wb.save(output_path)
    return output_path
```

## 必要的测试步骤

**每次生成工具后，必须生成测试文件验证符号显示正常！**

```python
from doc_tools.fonts import get_test_content
from doc_tools.pdf_generator import create_pdf_simple
from doc_tools.excel_generator import create_excel

# 测试PDF
test_content = get_test_content()
create_pdf_simple("/tmp/test_symbols.pdf", "符号测试", test_content)

# 测试Excel
test_data = [
    ["中文", "αβγ", "→", "≥", "©"],
    ["测试", "∑√", "↓", "≠", "®"],
]
create_excel("/tmp/test_symbols.xlsx", test_data, headers=["文字", "数学", "箭头", "符号", "特殊"])
```

## 常见问题与解决

### 问题1: PDF中文乱码
**原因**: 没有配置中文字体
**解决**: 使用ChinesePDF类，确保调用add_font()添加中文字体

### 问题2: Excel打开后乱码
**原因**: 使用了系统不支持的字体名称
**解决**: 使用'Noto Sans CJK SC'或系统已安装字体

### 问题3: 特殊符号显示为方框或问号
**原因**: 字体不支持该符号
**解决**: Noto Sans CJK SC支持大部分常用符号，如果不支持需要更换字体

## 可用模板

抄走即用的完整代码模板：

- `templates/fonts.py` - 字体配置中心（必复制）
- `templates/pdf_generator.py` - PDF生成器
- `templates/excel_generator.py` - Excel生成器
- `templates/ppt_generator.py` - PPT生成器
- `templates/utils.py` - 通用工具函数
- `templates/demo_example.py` - 完整使用示例

## 参考资料

- `references/package-structure.md` - 完整包结构说明

## 注意事项

1. **始终使用unicode支持的库**: fpdf2而不是fpdf（旧版）
2. **测试所有符号类型**: 中文、标点、数学符号、特殊符号
3. **保持字体配置中心化**: 所有文件从fonts.py导入字体配置
4. **先计划后执行**: 用户偏好先看到预算和计划再开始
