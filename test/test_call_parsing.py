#!/usr/bin/env python3
"""
测试函数调用解析
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer


def test_specific_function_calls():
    """测试特定函数的调用解析"""
    analyzer = RepoAnalyzer("test/miniz_config.json")
    analyzer.analyze()
    
    # 获取mz_compress2函数
    functions = analyzer.get_functions()
    mz_compress2_func = None
    
    for func in functions:
        if func.name == "mz_compress2" and not func.is_declaration:
            mz_compress2_func = func
            break
    
    if not mz_compress2_func:
        print("❌ 未找到mz_compress2函数")
        return
    
    print(f"📝 函数: {mz_compress2_func.name}")
    print(f"📁 文件: {mz_compress2_func.file_path}")
    print(f"📏 行数: {mz_compress2_func.start_line}-{mz_compress2_func.end_line}")
    
    # 强制重新解析
    mz_compress2_func.clear_call_cache()
    mz_compress2_func.parse_function_calls()
    
    print(f"\n🔧 解析结果:")
    print(f"解析状态: {mz_compress2_func._parsed_calls}")
    print(f"调用的函数: {mz_compress2_func.callees}")
    
    # 查看函数体
    print(f"\n📄 函数体:")
    body = mz_compress2_func.get_body()
    if body:
        lines = body.split('\n')
        for i, line in enumerate(lines, mz_compress2_func.start_line):
            print(f"{i:3}: {line}")
    
    # 手动测试正则表达式
    print(f"\n🔍 手动测试正则表达式:")
    import re
    
    function_call_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    test_lines = [
        "status = mz_deflateInit(&stream, level);",
        "status = mz_deflate(&stream, MZ_FINISH);",
        "mz_deflateEnd(&stream);",
        "return mz_deflateEnd(&stream);",
        "memset(&stream, 0, sizeof(stream));"
    ]
    
    for line in test_lines:
        matches = re.finditer(function_call_pattern, line)
        found_calls = [match.group(1) for match in matches]
        print(f"   '{line}' -> {found_calls}")


if __name__ == "__main__":
    test_specific_function_calls() 