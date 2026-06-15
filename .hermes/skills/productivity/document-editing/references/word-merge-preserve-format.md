# Word 文档合并 — 保留原始格式

## ⚠️ 重要：推荐方法

**不要用逐段复制的方法！** 经验证，简单复制段落和 run 会丢失：
- 表格网格线
- 字体格式（尤其是中文）
- 段落间距
- 分页符

**正确方法：使用底层 XML 复制（copy.deepcopy）** ✅

---

## 方法一：底层 XML 复制（推荐）

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
    output._body.clear()  # 清空默认内容
    
    for idx, (name, src_path) in enumerate(input_files):
        if not os.path.exists(src_path):
            print(f"❌ {name} 不存在: {src_path}")
            continue
            
        print(f"✅ 处理: {name}")
        src_doc = Document(src_path)
        
        # 获取源文档的 body 元素
        src_body = src_doc._body._element
        
        # 复制所有子元素（段落、表格、分页符等）
        for child in list(src_body):
            # 深拷贝每个子元素
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
    
    # 设置页面属性（使用最后一个文档的）
    if src_doc.sections:
        output.sections[0]._sectPr = copy.deepcopy(src_doc.sections[-1]._sectPr)
    
    output.save(output_path)
    print(f"\n✅ 已保存: {output_path}")
    return output
```

### 使用示例

```python
# 按毕业论文装订顺序
files = [
    ("封面", "/path/to/封面.docx"),
    ("独创性声明", "/path/to/独创性声明与版权使用授权书.docx"),
    ("任务书", "/path/to/任务书.docx"),
    ("开题报告", "/path/to/开题报告.docx"),
    ("指导记录表", "/path/to/指导记录表.docx"),
    ("论文正文", "/path/to/最终稿_稿件.docx"),
    ("评阅教师评分", "/path/to/评阅教师评分.docx"),
    ("答辩组评分", "/path/to/答辩组评分.docx"),
    ("成绩评定表", "/path/to/毕业论文（设计）成绩评定表.docx"),
]

merge_docs_xml_deepcopy(files, "/root/最终归档材料.docx")
```

### 关键点说明

1. **`copy.deepcopy(child)`** - 直接复制 XML 元素，保留所有格式
2. **`output._body.clear()`** - 清空默认空段落
3. **分页符** - 用 `OxmlElement` 手动创建 `<w:br w:type="page"/>`
4. **页面设置** - 复制最后一个文档的 `sectPr`

---

## 常见问题

### Q: 表格线还是没了？

用底层 XML 复制后表格线应该保留。如果还出问题，检查：
- 源文档的表格是否真的有边框（有些模板表格默认无边框）
- Word 打开后手动添加边框可能不被 XML 复制

### Q: 图片怎么处理？

对于简单图片复制，底层 XML 方法已经包含。如果有复杂图片处理需求，需要额外处理 `rels` 关系。

### Q: 封面有材料目录怎么处理？

封面文档可能包含材料目录（学生信息表格之后的目录页）。解决方案：
- 用 `doc.tables[0]` 只取学生信息表格
- 或识别并跳过包含"材料目录"关键字的段落/表格

---

## 毕业论文装订标准顺序

1. 封面（只保留学生信息，去掉材料目录）
2. 独创性声明与版权使用授权书
3. 任务书
4. 开题报告
5. 指导记录表
6. 论文正文（摘要→Abstract→目录→正文→致谢→参考文献）
7. 评阅教师评分
8. 答辩组评分
9. 成绩评定表
