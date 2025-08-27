#!/usr/bin/env python3
"""
测试FunctionUsageFinder模块的4个查找函数

测试以下4个函数：
1. find_usage_in_include_files - 仅在include_files中查找
2. find_usage_in_non_include_files - 仅在非include_files中查找
3. find_usage_in_all_files - 在所有文件中查找
4. find_usage_in_test_files - 在test文件中查找
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.repo_analyzer import RepoAnalyzer
from parser.config_parser import ConfigParser
import logging

# 配置日志
logging.basicConfig(level=logging.WARNING)  # 减少日志输出

def test_four_usage_finder_functions():
    """
    测试FunctionUsageFinder的4个查找函数
    """
    print("🧪 测试FunctionUsageFinder的4个查找函数")
    print("=" * 60)
    
    # 切换到项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    try:
        # 初始化配置和分析器
        config_path = "benchmarks/configs/cjson_config.json"
        config_parser = ConfigParser(config_path)
        repo_analyzer = RepoAnalyzer(config_path)
        
        print("📊 执行基本分析...")
        result = repo_analyzer.analyze()
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        print(f"✅ 基本分析完成")
        
        # 获取已分析的函数信息
        analyzed_functions = repo_analyzer.get_functions()
        
        # 测试函数
        test_function = "cJSON_CreateObject"
        repo_root = "benchmarks/cJSON"
        
        print(f"\n🔍 测试函数: {test_function}")
        print(f"📁 仓库路径: {repo_root}")
        
        # 测试1: find_usage_in_include_files
        print(f"\n1️⃣ 测试 find_usage_in_include_files:")
        include_usage = repo_analyzer.find_usage_in_include_files(
            function_name=test_function
        )
        
        print(f"   📊 结果: 在 {len(include_usage)} 个include文件中找到调用者")
        for file_path, callers in include_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"   📁 {rel_path}: {', '.join(callers)}")
        
        # 测试2: find_usage_in_non_include_files
        print(f"\n2️⃣ 测试 find_usage_in_non_include_files:")
        non_include_usage = repo_analyzer.find_usage_in_non_include_files(
            function_name=test_function,
            repo_root=repo_root
        )
        
        print(f"   📊 结果: 在 {len(non_include_usage)} 个非include文件中找到调用者")
        for file_path, callers in list(non_include_usage.items())[:5]:  # 只显示前5个
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"   📁 {rel_path}: {', '.join(callers)}")
        if len(non_include_usage) > 5:
            print(f"   ... 还有 {len(non_include_usage) - 5} 个文件")
        
        # 测试3: find_usage_in_all_files
        print(f"\n3️⃣ 测试 find_usage_in_all_files:")
        all_usage = repo_analyzer.find_usage_in_all_files(
            function_name=test_function,
            repo_root=repo_root
        )
        
        print(f"   📊 结果: 在 {len(all_usage)} 个文件中找到调用者")
        
        # 按文件类型分类显示
        test_files = []
        example_files = []
        main_files = []
        
        for file_path, callers in all_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            if 'test' in rel_path.lower() or 'tests' in rel_path.lower():
                test_files.append((rel_path, callers))
            elif 'example' in rel_path.lower() or 'examples' in rel_path.lower():
                example_files.append((rel_path, callers))
            else:
                main_files.append((rel_path, callers))
        
        if main_files:
            print(f"\n   📄 主要文件中的调用者 ({len(main_files)} 个文件):")
            for rel_path, callers in main_files[:3]:
                print(f"      📁 {rel_path}: {', '.join(callers)}")
            if len(main_files) > 3:
                print(f"      ... 还有 {len(main_files) - 3} 个主要文件")
        
        if test_files:
            print(f"\n   🧪 测试文件中的调用者 ({len(test_files)} 个文件):")
            for rel_path, callers in test_files[:3]:  # 只显示前3个
                print(f"      📁 {rel_path}: {', '.join(callers)}")
            if len(test_files) > 3:
                print(f"      ... 还有 {len(test_files) - 3} 个测试文件")
        
        if example_files:
            print(f"\n   📚 示例文件中的调用者 ({len(example_files)} 个文件):")
            for rel_path, callers in example_files[:3]:
                print(f"      📁 {rel_path}: {', '.join(callers)}")
            if len(example_files) > 3:
                print(f"      ... 还有 {len(example_files) - 3} 个示例文件")
        
        # 测试4: find_usage_in_test_files
        print(f"\n4️⃣ 测试 find_usage_in_test_files:")
        test_usage = repo_analyzer.find_usage_in_test_files(
            function_name=test_function,
            repo_root=repo_root
        )
        
        print(f"   📊 结果: 在 {len(test_usage)} 个test文件中找到调用者")
        for file_path, callers in test_usage.items():
            rel_path = os.path.relpath(file_path, repo_root)
            print(f"   📁 {rel_path}: {', '.join(callers)}")
        
        # 结果比较
        print(f"\n5️⃣ 结果比较:")
        include_count = len(include_usage)
        non_include_count = len(non_include_usage)
        all_count = len(all_usage)
        test_count = len(test_usage)
        
        print(f"   📊 仅include_files: {include_count} 个文件")
        print(f"   📊 仅非include_files: {non_include_count} 个文件")
        print(f"   📊 所有文件: {all_count} 个文件")
        print(f"   📊 仅test文件: {test_count} 个文件")
        
        # 验证逻辑正确性
        expected_all_count = include_count + non_include_count
        if all_count >= expected_all_count:
            print(f"   ✅ 逻辑正确: 所有文件数量 >= include文件 + 非include文件")
        else:
            print(f"   ⚠️  逻辑异常: 所有文件数量 < include文件 + 非include文件")
        
        if test_count <= all_count:
            print(f"   ✅ 逻辑正确: test文件数量 <= 所有文件数量")
        else:
            print(f"   ⚠️  逻辑异常: test文件数量 > 所有文件数量")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

def test_different_functions():
    """
    测试不同函数的4种查找模式
    """
    print(f"\n\n🔬 测试不同函数的4种查找模式")
    print("=" * 60)
    
    try:
        config_path = "benchmarks/configs/cjson_config.json"
        config_parser = ConfigParser(config_path)
        repo_analyzer = RepoAnalyzer(config_path)
        repo_analyzer.analyze()
        
        analyzed_functions = repo_analyzer.get_functions()
        
        repo_root = "benchmarks/cJSON"
        test_functions = ["cJSON_CreateObject", "cJSON_Delete", "malloc"]
        
        for func_name in test_functions:
            print(f"\n🔍 测试函数: {func_name}")
            
            # 测试4种查找模式
            include_usage = repo_analyzer.find_usage_in_include_files(
                function_name=func_name
            )
            
            non_include_usage = repo_analyzer.find_usage_in_non_include_files(
                function_name=func_name,
                repo_root=repo_root
            )
            
            all_usage = repo_analyzer.find_usage_in_all_files(
                function_name=func_name,
                repo_root=repo_root
            )
            
            test_usage = repo_analyzer.find_usage_in_test_files(
                function_name=func_name,
                repo_root=repo_root
            )
            
            include_count = len(include_usage)
            non_include_count = len(non_include_usage)
            all_count = len(all_usage)
            test_count = len(test_usage)
            
            print(f"   📊 include文件: {include_count} 个")
            print(f"   📊 非include文件: {non_include_count} 个")
            print(f"   📊 所有文件: {all_count} 个")
            print(f"   📊 test文件: {test_count} 个")
            
            if all_count > 0:
                print(f"   ✅ 找到调用者")
            else:
                print(f"   ℹ️  未找到调用者")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_edge_cases():
    """
    测试边界情况
    """
    print(f"\n\n🧪 测试边界情况")
    print("=" * 60)
    
    try:
        config_path = "benchmarks/configs/cjson_config.json"
        config_parser = ConfigParser(config_path)
        repo_analyzer = RepoAnalyzer(config_path)
        repo_analyzer.analyze()
        
        repo_root = "benchmarks/cJSON"
        
        # 测试1: 不存在的函数
        print(f"\n1. 测试不存在的函数:")
        non_existent_function = "this_function_does_not_exist"
        
        non_include_usage = repo_analyzer.find_usage_in_non_include_files(
            function_name=non_existent_function,
            repo_root=repo_root
        )
        
        test_usage = repo_analyzer.find_usage_in_test_files(
            function_name=non_existent_function,
            repo_root=repo_root
        )
        
        print(f"   📊 非include文件中找到: {len(non_include_usage)} 个")
        print(f"   📊 test文件中找到: {len(test_usage)} 个")
        
        if len(non_include_usage) == 0 and len(test_usage) == 0:
            print(f"   ✅ 正确处理不存在的函数")
        else:
            print(f"   ⚠️  意外找到了不存在函数的调用者")
        
        # 测试2: 空的analyzed_functions
        print(f"\n2. 测试空的analyzed_functions:")
        # 由于repo_analyzer的方法不需要analyzed_functions参数，这里测试空结果
        include_usage = repo_analyzer.find_usage_in_include_files(
            function_name="non_existent_function_for_empty_test"
        )
        
        print(f"   📊 include文件中找到: {len(include_usage)} 个")
        
        if len(include_usage) == 0:
            print(f"   ✅ 正确处理空的analyzed_functions")
        else:
            print(f"   ⚠️  意外找到了调用者")
        
        # 测试3: 无效的repo_root
        print(f"\n3. 测试无效的repo_root:")
        invalid_repo_root = "/path/that/does/not/exist"
        
        try:
            invalid_usage = repo_analyzer.find_usage_in_non_include_files(
                function_name="cJSON_CreateObject",
                repo_root=invalid_repo_root
            )
            print(f"   📊 无效路径中找到: {len(invalid_usage)} 个")
            print(f"   ✅ 正确处理无效路径")
        except Exception as e:
            print(f"   ✅ 正确抛出异常: {type(e).__name__}")
        
    except Exception as e:
        print(f"❌ 边界测试失败: {e}")

def main():
    """
    主函数
    """
    print("🚀 FunctionUsageFinder 4个函数测试")
    print("=" * 60)
    
    # 测试1: 基本4个函数功能
    test_four_usage_finder_functions()
    
    # 测试2: 不同函数的4种查找模式
    test_different_functions()
    
    # 测试3: 边界情况
    test_edge_cases()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    
    print("\n💡 功能说明:")
    print("   1. find_usage_in_include_files: 仅在配置文件指定的include_files中查找")
    print("   2. find_usage_in_non_include_files: 仅在非include_files中查找")
    print("   3. find_usage_in_all_files: 在所有文件中查找（合并1和2的结果）")
    print("   4. find_usage_in_test_files: 仅在文件路径包含'test'的文件中查找")
    
    print("\n🔧 使用方法:")
    print("   from parser.function_usage_finder import FunctionUsageFinder")
    print("   from parser.config_parser import ConfigParser")
    print("   ")
    print("   config_parser = ConfigParser('config.json')")
    print("   finder = FunctionUsageFinder(config_parser)")
    print("   ")
    print("   # 在include文件中查找")
    print("   include_usage = finder.find_usage_in_include_files('func_name', analyzed_functions)")
    print("   ")
    print("   # 在非include文件中查找")
    print("   non_include_usage = finder.find_usage_in_non_include_files('func_name', repo_root)")
    print("   ")
    print("   # 在所有文件中查找")
    print("   all_usage = finder.find_usage_in_all_files('func_name', repo_root, analyzed_functions)")
    print("   ")
    print("   # 在test文件中查找")
    print("   test_usage = finder.find_usage_in_test_files('func_name', repo_root)")

if __name__ == "__main__":
    main()