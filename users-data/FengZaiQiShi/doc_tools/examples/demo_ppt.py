#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT 生成示例
"""

import sys
sys.path.insert(0, '/root/users-data/FengZaiQiShi')

from doc_tools import PPTGenerator, create_simple_ppt, create_test_ppt


def demo_simple_ppt():
    """简单PPT示例"""
    print("=" * 50)
    print("示例1: 创建简单PPT")
    print("=" * 50)
    
    slides = [
        ('第一章 细胞的基本功能', '神经调节、体液调节和自身调节\n是机体对各种功能活动进行调节的三种基本方式'),
        ('第二章 神经传导', '神经元的基本功能\n• 接收刺激\n• 产生举叛\n• 传导冲动\n• 释放递质'),
        ('第三章 循环系统', '心脏的功能\n• 心电生理\n• 心跳动力学'),
    ]
    
    create_simple_ppt(
        output_path='/tmp/demo_simple.pptx',
        title='306生理学考研复习',
        content_slides=slides
    )
    
    print("✓ PPT已生成: /tmp/demo_simple.pptx")
    print()


def demo_advanced_ppt():
    """高级PPT示例"""
    print("=" * 50)
    print("示例2: 创建带多种字符的PPT")
    print("=" * 50)
    
    generator = PPTGenerator()
    
    slides = [
        {
            'title': '生理学基础概论',
            'content': '细胞的基本功能与神经传导',
            'layout': 'title'
        },
        {
            'title': '重要概念',
            'content': '''• 细胞膜电位：静息电位 + 动作电位
• 举叛电位: ≥ 余值电位
• 递质释放：大量释放→效应噪音
• 神经递质: 主要包括乙酰胆碱、多巴胺
            ''',
            'layout': 'title_and_content'
        },
        {
            'title': '数学符号',
            'content': '''数学符号示例：
α受体 β受体 γ受体 δ受体
≥ ≤ ≠ ≈ ±
× ÷ °C Ω ∞
            ''',
            'layout': 'title_and_content'
        },
        {
            'title': '评级与标注',
            'content': '''重要程度：★★★☆☆
难度：★★★★☆
考频：★★★★★

查看→ 详细说明
            ''',
            'layout': 'title_and_content'
        },
    ]
    
    generator.create_presentation('/tmp/demo_advanced.pptx', slides)
    
    print("✓ PPT已生成: /tmp/demo_advanced.pptx")
    print()


def demo_test_ppt():
    """测试PPT示例"""
    print("=" * 50)
    print("示例3: 创建完整测试PPT")
    print("=" * 50)
    
    create_test_ppt('/tmp/demo_test.pptx')
    print("✓ 测试PPT已生成: /tmp/demo_test.pptx")
    print()


def main():
    print("\n" + "=" * 50)
    print("PPT 生成工具示例")
    print("=" * 50 + "\n")
    
    try:
        demo_simple_ppt()
        demo_advanced_ppt()
        demo_test_ppt()
        
        print("=" * 50)
        print("所有示例已成功运行！")
        print("=" * 50)
        print("\n生成的文件：")
        print("  - /tmp/demo_simple.pptx")
        print("  - /tmp/demo_advanced.pptx")
        print("  - /tmp/demo_test.pptx")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
