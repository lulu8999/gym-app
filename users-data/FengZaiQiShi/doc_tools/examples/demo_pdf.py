#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 生成示例
"""

import sys
sys.path.insert(0, '/root/users-data/FengZaiQiShi')

from doc_tools import PDFGenerator, create_simple_pdf, create_test_pdf


def demo_simple_pdf():
    """简单PDF示例"""
    print("=" * 50)
    print("示例1: 创建简单PDF")
    print("=" * 50)
    
    output_path = '/tmp/demo_simple.pdf'
    
    create_simple_pdf(
        output_path=output_path,
        title='生理学考研资料',
        body='''第四版 细胞的基本功能

神经调节、体液调节和自身调节是机体对各种功能活动进行调节的三种基本方式。

关键概念：
• 细胞膜电位
• 动作电位
• 举叛电位

数学符号测试：αβγδ ≥ × ÷ °C
标点测试：，。！？；：（）【】《》
'''
    )
    
    print(f"✓ PDF已生成: {output_path}")
    print()


def demo_advanced_pdf():
    """高级PDF示例"""
    print("=" * 50)
    print("示例2: 创建带章节的PDF")
    print("=" * 50)
    
    generator = PDFGenerator(engine='fpdf')
    
    content = {
        'title': '生理学考研复习大纲',
        'sections': [
            {
                'heading': '第一章 细胞的基本功能',
                'body': '''本章主要内容包括：
1. 细胞的基本结构和功能
2. 细胞膜的物质转运功能
3. 细胞的信息传递功能

重要公式：
• 能斯特(E) = 动作电位 + 静息电位
• Nernst方程: E = (RT/zF) × ln([ion]外/[ion]内)

常用单位：mV、mM、μmol/L'''
            },
            {
                'heading': '第二章 神经系统功能',
                'body': '''神经元的基本功能：
1. 接收刺激
2. 产生举叛
3. 传导冲动
4. 释放递质

特殊符号测试：©®™ → ↑ ↓ ← ●★☆
货币符号：￥100元 €50 $30'''
            },
        ]
    }
    
    output_path = '/tmp/demo_advanced.pdf'
    generator.create_document(output_path, content)
    
    print(f"✓ PDF已生成: {output_path}")
    print()


def demo_test_pdf():
    """测试PDF示例 - 验证所有字符"""
    print("=" * 50)
    print("示例3: 创建完整测试PDF（验证所有字符）")
    print("=" * 50)
    
    output_path = '/tmp/demo_test_fpdf.pdf'
    create_test_pdf(output_path, engine='fpdf')
    print(f"✓ FPDF测试PDF已生成: {output_path}")
    
    output_path = '/tmp/demo_test_rl.pdf'
    create_test_pdf(output_path, engine='reportlab')
    print(f"✓ ReportLab测试PDF已生成: {output_path}")
    print()


def main():
    print("\n" + "=" * 50)
    print("PDF 生成工具示例")
    print("=" * 50 + "\n")
    
    try:
        demo_simple_pdf()
        demo_advanced_pdf()
        demo_test_pdf()
        
        print("=" * 50)
        print("所有示例已成功运行！")
        print("=" * 50)
        print("\n生成的文件：")
        print("  - /tmp/demo_simple.pdf")
        print("  - /tmp/demo_advanced.pdf")
        print("  - /tmp/demo_test_fpdf.pdf")
        print("  - /tmp/demo_test_rl.pdf")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
