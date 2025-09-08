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
        
        # 1. find_usage_in_repo
        print(f"\n1️⃣ find_usage_in_repo 结果:")
        print("=" * 50)
        
        all_usage = repo_analyzer.find_usage_in_repo(
            function_name=test_function
        )
        
        print(f"📊 在 {len(all_usage)} 个文件中找到usage")
        
        for file_path, callers in all_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"\n📁 文件: {rel_path}")
            caller_names = [caller['name'] for caller in callers] if callers else []
            print(f"   调用者函数: {', '.join(caller_names) if caller_names else '全局调用'}")
            
            # 显示调用者函数的完整代码
            if callers:
                for caller in callers:
                    print(f"\n   🔍 调用者函数 '{caller['name']}' 完整代码 (第{caller['start_line']}-{caller['end_line']}行):")
                    print("   " + "-" * 60)
                    code_lines = caller['code'].split('\n')
                    for i, line in enumerate(code_lines, start=caller['start_line']):
                        if line.strip():  # 只显示非空行
                            print(f"   {i:3d}: {line}")
                    print("   " + "-" * 60)
            

        
        # 2. 过滤测试文件的usage
        print(f"\n\n2️⃣ 测试文件中的usage 结果:")
        print("=" * 50)
        
        # 过滤出路径中包含测试关键词的文件
        test_keywords = ['test', 'example', 'demo', 'sample', 'tutorial']
        test_usage = {}
        
        for file_path, callers in all_usage.items():
            file_path_lower = file_path.lower()
            if any(keyword in file_path_lower for keyword in test_keywords):
                test_usage[file_path] = callers
        
        print(f"📊 在 {len(test_usage)} 个测试文件中找到usage")
        
        for file_path, callers in test_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"\n📁 测试文件: {rel_path}")
            caller_names = [caller['name'] for caller in callers] if callers else []
            print(f"   调用者函数: {', '.join(caller_names) if caller_names else '全局调用'}")
            
            # 显示调用者函数的完整代码
            if callers:
                for caller in callers:
                    print(f"\n   🔍 调用者函数 '{caller['name']}' 完整代码 (第{caller['start_line']}-{caller['end_line']}行):")
                    print("   " + "-" * 60)
                    code_lines = caller['code'].split('\n')
                    for i, line in enumerate(code_lines, start=caller['start_line']):
                        if line.strip():  # 只显示非空行
                            print(f"   {i:3d}: {line}")
                    print("   " + "-" * 60)
            

        
        # 总结
        print(f"\n\n📊 总结:")
        print(f"   仓库中的usage: {len(all_usage)} 个文件")
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
    print("   - 输出包含调用者函数的完整代码和位置信息")
    print("   - find_usage_in_repo: 在仓库的所有文件中查找")
    print("   - 测试文件过滤: 从所有结果中过滤出测试文件")

if __name__ == "__main__":
    main()