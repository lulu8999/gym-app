#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 生成示例
"""

import sys
sys.path.insert(0, '/root/users-data/FengZaiQiShi')

from doc_tools import ExcelGenerator, create_simple_excel, create_test_excel


def demo_simple_excel():
    """简单Excel示例"""
    print("=" * 50)
    print("示例1: 创建简单Excel")
    print("=" * 50)
    
    data = [
        ['张三', 20, '生理学', 85, '良好'],
        ['李四', 21, '生理学', 92, '优秀'],
        ['王五', 19, '解剖学', 78, '及格'],
        ['赵六', 20, '生理学', 88, '良好'],
    ]
    
    create_simple_excel(
        output_path='/tmp/demo_simple.xlsx',
        data=data,
        headers=['姓名', '年龄', '科目', '分数', '评语'],
        title='考研成绩测试表'
    )
    
    print("✓ Excel已生成: /tmp/demo_simple.xlsx")
    print()


def demo_with_symbols():
    """带符号的Excel示例"""
    print("=" * 50)
    print("示例2: 创建带符号的Excel")
    print("=" * 50)
    
    data = [
        ['α受体阻滞剂', '高血压', '≥100mg', '★★★☆☆'],
        ['β受体阻滞剂', '心绞痛', '≥50mg', '★★★★☆'],
        ['ACEI', '心力衰竭', '≥15mg', '★★★★★'],
        ['利尿剂', '水肿', '日剂量±1', '★★☆☆☆'],
    ]
    
    generator = ExcelGenerator(engine='openpyxl')
    generator.create_from_data(
        output_path='/tmp/demo_symbols.xlsx',
        data=data,
        headers=['药物名称', '适应症', '用量', '评级'],
        sheet_name='药物记录',
        title='常用药物一览表'
    )
    
    print("✓ Excel已生成: /tmp/demo_symbols.xlsx")
    print()


def demo_test_excel():
    """测试Excel示例"""
    print("=" * 50)
    print("示例3: 创建完整测试Excel")
    print("=" * 50)
    
    create_test_excel('/tmp/demo_test_openpyxl.xlsx', engine='openpyxl')
    print("✓ openpyxl测试Excel已生成: /tmp/demo_test_openpyxl.xlsx")
    
    create_test_excel('/tmp/demo_test_xlsxwriter.xlsx', engine='xlsxwriter')
    print("✓ xlsxwriter测试Excel已生成: /tmp/demo_test_xlsxwriter.xlsx")
    print()


def main():
    print("\n" + "=" * 50)
    print("Excel 生成工具示例")
    print("=" * 50 + "\n")
    
    try:
        demo_simple_excel()
        demo_with_symbols()
        demo_test_excel()
        
        print("=" * 50)
        print("所有示例已成功运行！")
        print("=" * 50)
        print("\n生成的文件：")
        print("  - /tmp/demo_simple.xlsx")
        print("  - /tmp/demo_symbols.xlsx")
        print("  - /tmp/demo_test_openpyxl.xlsx")
        print("  - /tmp/demo_test_xlsxwriter.xlsx")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
