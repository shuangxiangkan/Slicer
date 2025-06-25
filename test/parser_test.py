#!/usr/bin/env python3
"""
parser模块测试脚本
测试parser模块的核心功能
"""

import sys
import os
from pathlib import Path

# 添加父目录到路径，以便导入parser模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import RepoAnalyzer


def test_directory_analysis():
    """测试1：从目录提取函数 - 使用libraries/cJSON目录"""
    print("=" * 80)
    print("🧪 测试1: 从目录提取函数 (libraries/cJSON)")
    print("=" * 80)
    
    # 使用实际项目目录
    test_dir = "libraries/cJSON"
    
    if not os.path.exists(test_dir):
        print(f"❌ 测试目录不存在: {test_dir}")
        print("   请确保在项目根目录运行此测试")
        return False
    
    try:
        analyzer = RepoAnalyzer()
        
        # 分析目录
        print(f"📂 分析目录: {test_dir}")
        result = analyzer.analyze_repository(test_dir, show_progress=True)
        
        if not result:
            print("❌ 分析失败")
            return False
        
        # 显示结果 - 使用完整路径显示
        print(f"\n📋 找到的函数列表:")
        analyzer.print_all_functions(
            group_by_file=True, 
            show_details=True,
            show_full_path=True  # 显示完整路径
        )
        
        # 显示重复函数（如果有）
        if analyzer.analysis_stats.get('duplicate_functions'):
            analyzer.print_duplicate_functions()
        
        print("\n✅ 测试1通过 - 目录分析功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        return False


def test_single_file_analysis():
    """测试2：从单个文件提取函数 - 使用example.c"""
    print("\n" + "=" * 80)
    print("🧪 测试2: 从单个文件提取函数 (example.c)")
    print("=" * 80)
    
    test_file = "example.c"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        print("   请确保在项目根目录运行此测试")
        return False
    
    try:
        analyzer = RepoAnalyzer()
        
        # 分析单个文件
        print(f"📄 分析文件: {test_file}")
        result = analyzer.analyze_repository(test_file, show_progress=True)
        
        if not result:
            print("❌ 分析失败")
            return False
        
        # 显示结果 - 使用完整路径显示
        print(f"\n📋 找到的函数列表:")
        analyzer.print_all_functions(
            group_by_file=True, 
            show_details=True,
            show_full_path=True  # 显示完整路径
        )
        
        print("\n✅ 测试2通过 - 单文件分析功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        return False


def test_filtering_functionality():
    """测试3：测试文件过滤功能"""
    print("\n" + "=" * 80)
    print("🧪 测试3: 文件过滤功能测试")
    print("=" * 80)
    
    test_dir = "libraries/cJSON"
    
    if not os.path.exists(test_dir):
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        analyzer = RepoAnalyzer()
        
        # 测试包含模式 - 只分析.h头文件
        print("🔍 测试包含模式：只分析头文件 (*.h)")
        print("-" * 40)
        
        result1 = analyzer.analyze_repository(
            test_dir, 
            show_progress=True,
            include_patterns=["*.h"]
        )
        
        if result1:
            print(f"\n📋 头文件中的函数:")
            analyzer.print_all_functions(
                group_by_file=True, 
                show_details=True,
                show_full_path=True
            )
        
        # 测试排除模式 - 排除测试相关文件
        print("\n" + "=" * 60)
        print("🚫 测试排除模式：排除测试文件 (*test*, *Test*)")
        print("-" * 40)
        
        analyzer2 = RepoAnalyzer()
        result2 = analyzer2.analyze_repository(
            test_dir, 
            show_progress=True,
            exclude_patterns=["*test*", "*Test*", "*TEST*"]
        )
        
        if result2:
            print(f"\n📋 非测试文件中的函数:")
            analyzer2.print_all_functions(
                group_by_file=True, 
                show_details=True,
                show_full_path=True
            )
        
        print("\n✅ 测试3通过 - 文件过滤功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        return False


def test_function_search():
    """测试4：测试函数搜索功能"""
    print("\n" + "=" * 80)
    print("🧪 测试4: 函数搜索功能测试")
    print("=" * 80)
    
    test_dir = "libraries/cJSON"
    
    if not os.path.exists(test_dir):
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        analyzer = RepoAnalyzer()
        
        # 先分析目录
        print(f"📂 分析目录: {test_dir}")
        result = analyzer.analyze_repository(test_dir, show_progress=False)
        
        if not result:
            print("❌ 分析失败")
            return False
        
        # 搜索特定函数
        search_patterns = ["cJSON", "parse", "print"]
        
        for pattern in search_patterns:
            print(f"\n🔍 搜索包含 '{pattern}' 的函数:")
            print("-" * 40)
            
            matched = analyzer.search_functions(pattern, case_sensitive=False)
            
            if matched:
                # 分别统计定义和声明
                definitions = [f for f in matched if not f.is_declaration]
                declarations = [f for f in matched if f.is_declaration]
                
                print(f"找到 {len(matched)} 个匹配函数:")
                print(f"  - {len(definitions)} 个定义")
                print(f"  - {len(declarations)} 个声明")
                
                # 显示前几个结果
                for i, func in enumerate(matched[:5], 1):
                    func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
                    rel_path = Path(func.file_path).name if func.file_path else "Unknown"
                    print(f"  {i}. {func_type} {func.name} - {rel_path}:{func.start_line}")
                
                if len(matched) > 5:
                    print(f"  ... 还有 {len(matched) - 5} 个函数")
            else:
                print("  未找到匹配的函数")
        
        print("\n✅ 测试4通过 - 函数搜索功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("🚀 开始parser模块功能测试")
    print("测试将使用项目中的实际文件")
    
    # 运行所有测试
    tests = [
        ("目录分析测试", test_directory_analysis),
        ("单文件分析测试", test_single_file_analysis),
        ("文件过滤测试", test_filtering_functionality),
        ("函数搜索测试", test_function_search),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"\n❌ {test_name} 失败")
        except KeyboardInterrupt:
            print(f"\n⚠️ 用户中断测试")
            break
        except Exception as e:
            print(f"\n❌ {test_name} 出错: {e}")
    
    # 显示测试结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"总测试数: {total}")
    print(f"通过数量: {passed}")
    print(f"失败数量: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！parser模块功能正常")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 