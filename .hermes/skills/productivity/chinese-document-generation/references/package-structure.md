# doc_tools 完整包结构参考

本会话完整实现的包结构，可作为参考：

```
doc_tools/
├── __init__.py              # 包入口
├── fonts.py                 # 字体配置中心
├── pdf_generator.py         # PDF生成工具
├── excel_generator.py       # Excel生成工具
├── ppt_generator.py         # PPT生成工具
├── utils.py                 # 通用工具函数
└── examples/
    ├── __init__.py
    ├── demo_pdf.py
    ├── demo_excel.py
    └── demo_ppt.py
```

## 完整实现路径

位置: `/root/users-data/FengZaiQiShi/doc_tools/`

## 使用方式

```python
from doc_tools import create_simple_pdf, create_simple_excel, create_simple_ppt

# 快速生成文档
create_simple_pdf('output.pdf', '标题', '内容')
create_simple_excel('output.xlsx', data, headers=['列1', '列2'])
create_simple_ppt('output.pptx', '标题', [('第1页', '内容')])
```

## 测试验证

运行测试命令：
```bash
cd doc_tools
python3 pdf_generator.py
python3 excel_generator.py
python3 ppt_generator.py
```

## 支持的字符

所有生成器都支持：
- 中文（简体/繁体）
- 标点符号
- 数学符号（αβγ∑√等）
- 特殊符号（©®™●★等）
- 箭头符号
- 货币符号

## 字体回退机制

fonts.py 提供多级字体回退：
1. Noto Sans CJK SC（优先）
2. Microsoft YaHei
3. SimHei
4. SimSun
5. Arial Unicode MS

## 引擎选择

PDF: fpdf2 / reportlab
Excel: openpyxl / xlsxwriter
PPT: python-pptx (单一引擎)
