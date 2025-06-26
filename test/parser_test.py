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
        if ret_info.is_actually_pointer():
            print(f"   └─ {ret_info.get_pointer_analysis()}")
        if ret_info.is_const:
            print(f"   └─ const修饰")
        if ret_info.is_basic_type():
            print(f"   └─ 基本类型")
        else:
            print(f"   └─ 自定义类型")
        
        # 返回类型链信息
        ret_type_chain = ret_info.get_type_chain()
        if len(ret_type_chain) > 1:
            print(f"   └─ 类型链: {' → '.join(ret_type_chain)}")
        
        # 参数详细信息
        if func.parameter_details:
            print(f"📋 参数列表 ({len(func.parameter_details)} 个):")
            for j, param in enumerate(func.parameter_details, 1):
                print(f"   {j:2}. {param.get_full_signature()}")
                
                # 参数特征
                features = []
                if param.is_actually_pointer():
                    features.append(param.get_pointer_analysis())
                if param.is_const:
                    features.append("const")
                if param.is_reference:
                    features.append("引用")
                if param.is_basic_type():
                    features.append("基本类型")
                else:
                    features.append("自定义类型")
                
                # 类型链信息
                type_chain = param.get_type_chain()
                if len(type_chain) > 1:
                    features.append(f"类型链: {' → '.join(type_chain)}")
                
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


def test_pointer_classification(analyzer: RepoAnalyzer):
    """测试功能4: 按指针参数和返回值数量分类函数"""
    print(f"\n🎯 测试功能4: 按指针参数和返回值数量分类函数")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    
    # 只分析函数定义，跳过声明
    definitions = [f for f in functions if not f.is_declaration]
    
    # 分类存储
    pointer_categories = {
        0: [],  # 0个指针
        1: [],  # 1个指针
        2: [],  # 2个指针
        3: []   # 3个及以上指针
    }
    
    # 对每个函数进行分类
    for func in definitions:
        # 计算指针参数数量
        pointer_param_count = sum(1 for param in func.parameter_details if param.is_actually_pointer())
        
        # 计算指针返回值数量（0或1）
        pointer_return_count = 1 if func.return_type_details.is_actually_pointer() else 0
        
        # 总指针数量
        total_pointer_count = pointer_param_count + pointer_return_count
        
        # 分类
        if total_pointer_count >= 3:
            pointer_categories[3].append(func)
        else:
            pointer_categories[total_pointer_count].append(func)
    
    # 显示分类结果
    print(f"📊 按指针数量分类统计:")
    print(f"   总函数定义数: {len(definitions)}")
    for category, funcs in pointer_categories.items():
        if category == 3:
            print(f"   {category}个及以上指针: {len(funcs)} 个函数")
        else:
            print(f"   {category}个指针: {len(funcs)} 个函数")
    print()
    
    # 详细显示每个分类
    for category, funcs in pointer_categories.items():
        if not funcs:
            continue
            
        if category == 3:
            print(f"🔴 {category}个及以上指针参数或返回值的函数 ({len(funcs)} 个):")
        else:
            print(f"🟢 {category}个指针参数或返回值的函数 ({len(funcs)} 个):")
        print("-" * 60)
        
        for i, func in enumerate(funcs, 1):
            # 计算详细指针信息
            pointer_params = [p for p in func.parameter_details if p.is_actually_pointer()]
            has_pointer_return = func.return_type_details.is_actually_pointer()
            
            print(f"   [{i:2}] {func.get_detailed_signature()}")
            print(f"        📁 {func.file_path}:{func.start_line}")
            
            # 显示指针详情
            pointer_details = []
            
            if has_pointer_return:
                ret_analysis = func.return_type_details.get_pointer_analysis()
                pointer_details.append(f"返回值: {ret_analysis}")
            
            if pointer_params:
                param_analyses = []
                for param in pointer_params:
                    param_analysis = f"{param.name}({param.get_pointer_analysis()})"
                    param_analyses.append(param_analysis)
                pointer_details.append(f"参数: {', '.join(param_analyses)}")
            
            if pointer_details:
                print(f"        🎯 指针详情: {'; '.join(pointer_details)}")
            
            # 每5个函数加一个分隔线
            if i % 5 == 0 and i < len(funcs):
                print("        " + "·" * 40)
        
        print()
    
    # 统计摘要
    print(f"📈 指针使用模式分析:")
    print("-" * 40)
    
    # 最复杂的函数（指针最多）
    if pointer_categories[3]:
        most_complex = max(pointer_categories[3], 
                          key=lambda f: len([p for p in f.parameter_details if p.is_actually_pointer()]) + 
                                       (1 if f.return_type_details.is_actually_pointer() else 0))
        pointer_count = len([p for p in most_complex.parameter_details if p.is_actually_pointer()]) + \
                       (1 if most_complex.return_type_details.is_actually_pointer() else 0)
        print(f"   指针最多的函数: {most_complex.name} ({pointer_count}个指针)")
    
    # 无指针函数分析
    no_pointer_funcs = pointer_categories[0]
    if no_pointer_funcs:
        print(f"   无指针函数占比: {len(no_pointer_funcs)/len(definitions)*100:.1f}%")
        
        # 分析无指针函数的特点
        basic_return_count = sum(1 for f in no_pointer_funcs if f.return_type_details.is_basic_type())
        print(f"   无指针函数中返回基本类型的: {basic_return_count} 个 ({basic_return_count/len(no_pointer_funcs)*100:.1f}%)")
    
    # 指针密集度分析
    total_pointer_usage = sum(len(funcs) * category for category, funcs in pointer_categories.items() if category < 3)
    if pointer_categories[3]:
        # 为3+类别估算平均指针数
        avg_pointers_in_complex = sum(
            len([p for p in f.parameter_details if p.is_actually_pointer()]) + 
            (1 if f.return_type_details.is_actually_pointer() else 0)
            for f in pointer_categories[3]
        ) / len(pointer_categories[3])
        total_pointer_usage += len(pointer_categories[3]) * avg_pointers_in_complex
    
    avg_pointers_per_func = total_pointer_usage / len(definitions) if definitions else 0
    print(f"   平均每个函数指针数: {avg_pointers_per_func:.2f}")


def test_library_analysis():
    """测试库文件分析功能"""
    print("🧪 库文件分析测试")
    print("=" * 80)
    
    # 使用test目录下的配置文件路径
    config_path = os.path.join(os.path.dirname(__file__), "miniz_config.json")
    
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
            
            # # 测试功能3: 详细的参数和返回值信息
            # test_detailed_parameter_info(analyzer)
            
            # 测试功能4: 按指针参数和返回值数量分类函数
            test_pointer_classification(analyzer)
            
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