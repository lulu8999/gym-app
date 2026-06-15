#!/usr/bin/env python3
"""
doc_tools 完整包示例
使用示例和测试代码
"""

import sys
sys.path.insert(0, '/path/to/doc_tools')

from doc_tools import (
    PDFGenerator, ExcelGenerator, PPTGenerator,
    create_simple_pdf, create_simple_excel, create_simple_ppt,
    get_test_content
)


def demo_all():
    """运行所有示例"""
    print("生成测试文档...")
    
    # PDF示例
    test_content = get_test_content()
    create_simple_pdf(
        '/tmp/demo_chinese.pdf',
        '中文测试',
        test_content
    )
    print("✓ PDF已生成: /tmp/demo_chinese.pdf")
    
    # Excel示例
    data = [
        ['张三', '生理学', 85, 'αβγ'],
        ['李四', '解剖学', 92, '∑√'],
    ]
    create_simple_excel(
        '/tmp/demo_chinese.xlsx',
        data,
        headers=['姓名', '科目', '分数', '符号'],
        title='成绩单'
    )
    print("✓ Excel已生成: /tmp/demo_chinese.xlsx")
    
    # PPT示例
    create_simple_ppt(
        '/tmp/demo_chinese.pptx',
        '考研复习',
        [('第一章', '细胞的基本功能'),
         ('第二章', '神经传导')]
    )
    print("✓ PPT已生成: /tmp/demo_chinese.pptx")
    
    print("\n所有文件已生成，请检查符号显示是否正常。")


if __name__ == "__main__":
    demo_all()
