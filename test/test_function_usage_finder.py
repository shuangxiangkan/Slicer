#!/usr/bin/env python3
"""
简化的FunctionUsageFinder测试
测试cJSON API的usage查找功能
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.repo_analyzer import RepoAnalyzer
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)  # 减少日志输出

def get_usage_details(file_path, function_name):
    """
    获取函数在文件中的详细usage信息
    返回: [(line_number, context_lines), ...]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        usages = []
        for i, line in enumerate(lines, 1):
            if function_name in line:
                # 获取前三行代码作为上下文
                start_idx = max(0, i - 3)
                context_lines = []
                for j in range(start_idx, min(len(lines), i)):
                    context_lines.append(f"{j+1:4d}: {lines[j].rstrip()}")
                
                usages.append((i, context_lines))
        
        return usages
    except Exception as e:
        print(f"   ❌ 读取文件失败 {file_path}: {e}")
        return []

def test_cjson_api_usage():
    """
    测试cJSON API的usage查找
    """
    print("🧪 测试cJSON API Usage查找")
    print("=" * 60)
    
    # 切换到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    try:
        # 初始化配置和分析器
        config_path = "benchmarks/configs/cjson_config.json"
        repo_analyzer = RepoAnalyzer(config_path)
        
        print("📊 执行基本分析...")
        result = repo_analyzer.analyze()
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        print(f"✅ 基本分析完成")
        
        # 测试函数 - 可以手动修改这里
        test_function = "cJSON_ParseWithLength"
        repo_root = "benchmarks/cJSON"
        
        print(f"\n🔍 测试函数: {test_function}")
        print(f"📁 仓库路径: {repo_root}")
        
        # 1. find_usage_in_all_files
        print(f"\n1️⃣ find_usage_in_all_files 结果:")
        print("=" * 50)
        
        all_usage = repo_analyzer.find_usage_in_all_files(
            function_name=test_function
        )
        
        print(f"📊 在 {len(all_usage)} 个文件中找到usage")
        
        for file_path, callers in all_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"\n📁 文件: {rel_path}")
            print(f"   调用者函数: {', '.join(callers) if callers else '全局调用'}")
            
            # 获取详细的usage信息
            usages = get_usage_details(file_path, test_function)
            
            for line_num, context_lines in usages:
                print(f"\n   📍 第 {line_num} 行:")
                for context_line in context_lines:
                    if str(line_num) in context_line and test_function in context_line:
                        print(f"   ➤ {context_line}")  # 高亮当前行
                    else:
                        print(f"     {context_line}")
        
        # 2. find_usage_in_test_files
        print(f"\n\n2️⃣ find_usage_in_test_files 结果:")
        print("=" * 50)
        
        test_usage = repo_analyzer.find_usage_in_test_files(
            function_name=test_function
        )
        
        print(f"📊 在 {len(test_usage)} 个测试文件中找到usage")
        
        for file_path, callers in test_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"\n📁 测试文件: {rel_path}")
            print(f"   调用者函数: {', '.join(callers) if callers else '全局调用'}")
            
            # 获取详细的usage信息
            usages = get_usage_details(file_path, test_function)
            
            for line_num, context_lines in usages:
                print(f"\n   📍 第 {line_num} 行:")
                for context_line in context_lines:
                    if str(line_num) in context_line and test_function in context_line:
                        print(f"   ➤ {context_line}")  # 高亮当前行
                    else:
                        print(f"     {context_line}")
        
        # 总结
        print(f"\n\n📊 总结:")
        print(f"   所有文件中的usage: {len(all_usage)} 个文件")
        print(f"   测试文件中的usage: {len(test_usage)} 个文件")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    主函数
    """
    print("🚀 简化的cJSON API Usage测试")
    print("=" * 60)
    
    # 测试cJSON API的usage查找
    test_cjson_api_usage()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    
    print("\n💡 说明:")
    print("   - 可以修改 test_function 变量来测试不同的cJSON API")
    print("   - 输出包含文件路径、行号和前三行代码上下文")
    print("   - find_usage_in_all_files: 在所有文件中查找")
    print("   - find_usage_in_test_files: 仅在测试文件中查找")

if __name__ == "__main__":
    main()