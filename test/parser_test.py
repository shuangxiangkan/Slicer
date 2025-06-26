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
    summary.print_all_functions(group_by_file=True, show_signatures=False)


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


def test_detailed_parameter_info(analyzer: RepoAnalyzer):
    """测试功能3: 详细的参数和返回值信息"""
    print(f"\n🔬 测试功能3: 详细的参数和返回值信息")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    
    # 只分析函数定义，跳过声明
    definitions = [f for f in functions if not f.is_declaration]
    
    print(f"📋 所有函数详细签名和参数信息 ({len(definitions)} 个函数定义):")
    print("=" * 100)
    
    for i, func in enumerate(definitions, 1):
        print(f"\n[{i:3}/{len(definitions)}] 🔧 函数: {func.name}")
        print("-" * 80)
        
        # 打印详细签名
        print(f"📝 详细签名: {func.get_detailed_signature()}")
        print(f"📁 位置: {func.file_path}:{func.start_line}-{func.end_line}")
        if func.scope:
            print(f"📂 作用域: {func.scope}")
        
        # 返回类型详细信息
        ret_info = func.return_type_details
        print(f"↩️  返回类型: {ret_info.get_type_signature()}")
        if ret_info.is_pointer:
            print(f"   └─ 指针层级: {ret_info.pointer_level}")
        if ret_info.is_const:
            print(f"   └─ const修饰")
        if ret_info.is_basic_type():
            print(f"   └─ 基本类型")
        else:
            print(f"   └─ 自定义类型")
        
        # 参数详细信息
        if func.parameter_details:
            print(f"📋 参数列表 ({len(func.parameter_details)} 个):")
            for j, param in enumerate(func.parameter_details, 1):
                print(f"   {j:2}. {param.get_full_signature()}")
                
                # 参数特征
                features = []
                if param.is_pointer:
                    features.append(f"指针(层级:{param.pointer_level})")
                if param.is_const:
                    features.append("const")
                if param.is_reference:
                    features.append("引用")
                if param.is_basic_type():
                    features.append("基本类型")
                else:
                    features.append("自定义类型")
                
                if features:
                    print(f"      └─ {', '.join(features)}")
        else:
            print(f"📋 参数列表: 无参数")
        
        # 函数特征摘要
        summary = func.get_parameter_summary()
        if summary['total_params'] > 0:
            print(f"📊 参数摘要: 总数:{summary['total_params']}, 指针:{summary['pointer_params']}, const:{summary['const_params']}, 基本类型:{summary['basic_type_params']}")
        
        # # 每5个函数暂停一下，避免输出过多
        # if i % 5 == 0 and i < len(definitions):
        #     choice = input(f"\n--- 已显示前 {i} 个函数，按回车键继续查看后续函数（输入 's' 跳到统计信息）... ---").strip().lower()
        #     if choice == 's':
        #         break
    
    # 打印全局统计分析
    print(f"\n\n🔬 全局参数和返回类型统计分析")
    print("=" * 80)
    
    summary = analyzer.get_summary()
    summary.print_parameter_analysis()


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
            
            # # 测试功能1: 打印所有函数
            # test_print_all_functions(analyzer)
            
            # # 测试功能2: 根据函数名打印函数体
            # test_print_function_body(analyzer)
            
            # 测试功能3: 详细的参数和返回值信息
            test_detailed_parameter_info(analyzer)
            
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