#!/usr/bin/env python3
"""
解析器测试脚本 - 基于用户配置文件的代码分析测试
"""

import sys
import os
from pathlib import Path

# 添加上级目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from parser.repo_analyzer import RepoAnalyzer


def test_print_all_functions(analyzer: RepoAnalyzer):
    """测试功能1: 打印repo中的所有函数"""
    print(f"\n📋 测试功能1: 打印所有函数")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    summary = analyzer.get_summary()
    
    print(f"📊 函数统计:")
    print(f"   总函数数: {len(functions)}")
    definitions = [f for f in functions if not f.is_declaration]
    declarations = [f for f in functions if f.is_declaration]
    print(f"   函数定义: {len(definitions)}")
    print(f"   函数声明: {len(declarations)}")
    
    # 打印所有函数列表
    summary.print_all_functions(group_by_file=True, show_details=False)


def test_print_function_body(analyzer: RepoAnalyzer):
    """测试功能2: 根据函数名打印函数体"""
    print(f"\n🔍 测试功能2: 根据函数名打印函数体")
    print("=" * 80)
    
    summary = analyzer.get_summary()
    functions = analyzer.get_functions()
    
    # 测试几个具体的函数
    test_functions = ["cJSON_CreateNull", "cJSON_Parse", "cJSON_Delete"]
    
    for func_name in test_functions:
        print(f"\n🔍 查找函数: {func_name}")
        summary.print_function_body(func_name, functions, exact_match=True, show_metadata=True)
        print("\n" + "-" * 80)


def test_library_analysis():
    """测试库文件分析功能"""
    print("🧪 库文件分析测试")
    print("=" * 80)
    
    # 使用test目录下的配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), "user_config.json")
    
    try:
        # 创建分析器实例
        analyzer = RepoAnalyzer(config_path)
        
        # 执行分析
        result = analyzer.analyze(show_progress=True)
        
        if result:
            print(f"\n✅ 分析成功完成!")
            print(f"📁 处理文件: {result['processed_files']}/{result['total_files']}")
            print(f"🎯 总函数数: {result['total_functions']}")
            print(f"🔧 函数定义: {result['function_definitions']}")
            print(f"🔗 函数声明: {result['function_declarations']}")
            print(f"⏱️  处理时间: {result['processing_time']:.3f}秒")
            
            # 测试功能1: 打印所有函数
            test_print_all_functions(analyzer)
            
            # 测试功能2: 根据函数名打印函数体
            test_print_function_body(analyzer)
            
        else:
            print("❌ 分析失败 - 无结果")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("🚀 代码分析器测试")
    print("=" * 80)
    
    test_library_analysis()
    
    print("\n🏁 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main() 