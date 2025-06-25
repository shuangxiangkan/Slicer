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
            
            # 使用summary模块显示结果
            summary = analyzer.get_summary()
            
            # 显示部分函数列表
            print(f"\n📋 找到的部分函数:")
            functions = analyzer.get_functions()
            for i, func in enumerate(functions[:10], 1):
                func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
                file_name = os.path.basename(func.file_path) if func.file_path else "Unknown"
                print(f"  {i:2}. {func_type} {func.name} - {file_name}:{func.start_line}")
            
            if len(functions) > 10:
                print(f"     ... 还有 {len(functions) - 10} 个函数")
            
            # 函数搜索测试
            print(f"\n🔍 函数搜索测试:")
            search_terms = ["cJSON_Create", "parse", "print"]
            
            for term in search_terms:
                matches = analyzer.search_functions(term)
                summary.print_search_results(term, matches, max_display=3)
                print()
        else:
            print("❌ 分析失败 - 无结果")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("💡 配置文件说明:")
    print("配置文件路径: test/user_config.json")
    print("配置项说明:")
    print("  - library_path: 要分析的库文件夹的绝对路径")
    print("  - include_files: 要包含的文件列表（相对于library_path）")
    print("  - exclude_files: 要排除的文件列表（相对于library_path）")
    print("\n使用规则:")
    print("- 如果指定了include_files，则只分析这些文件（包含模式）")
    print("- 如果指定了exclude_files，则分析整个库但排除这些文件（排除模式）")
    print("- include_files和exclude_files不能同时指定（互斥）")
    print("- 如果都不指定，则分析整个库")
    print("=" * 80)


def main():
    """主测试函数"""
    print("🚀 代码分析器测试")
    print("=" * 80)
    
    test_library_analysis()
    
    print("\n🏁 测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main() 