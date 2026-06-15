#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体配置中心 - 确保中文显示正常
复制此文件到你的项目中使用
"""

import os

# 字体优先级列表（按优先顺序尝试）
FONT_PATHS = [
    '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
    '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

# 字体名称列表（用于Excel/PPT等）
FONT_NAMES = [
    'Noto Sans CJK SC',
    'Noto Sans SC', 
    'Source Han Sans SC',
    'Microsoft YaHei',
    'SimHei',
    'SimSun',
    'Arial Unicode MS',
    'DejaVu Sans',
]

def get_available_font_path():
    """获取第一个可用的字体文件路径"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return path
    # 如果都不存在，尝试查找fontconfig
    try:
        import subprocess
        result = subprocess.run(['fc-list', ':lang=zh', '-f', '%{file}\n'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout:
            first_font = result.stdout.strip().split('\n')[0]
            if first_font:
                return first_font
    except:
        pass
    return None

def get_font_name(prefer_index=0):
    """
    获取推荐的字体名称
    
    参数:
        prefer_index: 偏好索引，0表示最优先
    """
    if prefer_index < len(FONT_NAMES):
        return FONT_NAMES[prefer_index]
    return FONT_NAMES[0]

# 符号测试集（用于验证显示效果）
TEST_SYMBOLS = {
    'chinese': '中文测试内容，包含简体和繁體字段',
    'punctuation': '，。！？；：（）【】《》「」『』‘’“”～·——，、',
    'special': '©®™°±×÷…——●★☆○◆•＊▲▼',
    'math': 'αβγδεζηθικλμνξοπρστυφχψω∑∏√∞≤≥≠≈°′″℃Ω',
    'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕⇦⇧⇨⇩',
    'currency': '￥¥$€£¢₹₩',
}

def get_test_content():
    """获取完整测试内容"""
    lines = ["文档生成测试 - 符号显示验证", "=" * 40]
    for category, content in TEST_SYMBOLS.items():
        lines.append(f"\n[{category}]")
        lines.append(content)
    return '\n'.join(lines)

def get_test_data():
    """获取Excel测试数据"""
    return [
        ["类别", "示例1", "示例2", "示例3"],
        ["中文", "测试", "示例", "文字"],
        ["数学", "αβγ", "∑√", "≥≠"],
        ["箭头", "←↑", "⇒⇓", "⇔↔"],
        ["特殊", "©®", "™°", "★☆"],
    ]

if __name__ == "__main__":
    print("字体路径:", get_available_font_path())
    print("字体名称:", get_font_name())
    print("\n测试内容:")
    print(get_test_content())
