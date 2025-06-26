#!/usr/bin/env python3
"""
解析器测试脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer
from parser.config_parser import ConfigParser


def test_print_all_functions(analyzer: RepoAnalyzer):
    """测试功能1: 打印所有函数"""
    print(f"\n🔍 测试功能1: 打印所有函数")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    
    print(f"📊 函数统计:")
    print(f"   总函数数: {len(functions)}")
    definitions = [f for f in functions if not f.is_declaration]
    declarations = [f for f in functions if f.is_declaration]
    print(f"   函数定义: {len(definitions)}")
    print(f"   函数声明: {len(declarations)}")
    
    # 按文件分组显示
    file_groups = {}
    for func in functions:
        file_name = Path(func.file_path).name
        if file_name not in file_groups:
            file_groups[file_name] = []
        file_groups[file_name].append(func)
    
    print(f"\n📋 所有函数列表:")
    print("=" * 80)
    
    for file_name, funcs in file_groups.items():
        file_defs = [f for f in funcs if not f.is_declaration]
        file_decls = [f for f in funcs if f.is_declaration]
        
        print(f"\n📁 {file_name}")
        print(f"   ({len(file_defs)} 个定义 + {len(file_decls)} 个声明 = {len(funcs)} 个函数)")
        print("-" * 60)
        
        # 按行号排序
        sorted_funcs = sorted(funcs, key=lambda x: x.start_line)
        
        for i, func in enumerate(sorted_funcs, 1):
            func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
            print(f"{i:3}. {func_type} {func.name}")


def test_print_function_body(analyzer: RepoAnalyzer):
    """测试功能2: 根据函数名打印函数体"""
    print(f"\n🔍 测试功能2: 根据函数名打印函数体")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    
    # 测试几个具体的函数
    test_functions = ["cJSON_CreateNull", "cJSON_Parse", "cJSON_Delete"]
    
    for func_name in test_functions:
        print(f"\n🔍 查找函数: {func_name}")
        
        # 查找匹配的函数
        matches = [f for f in functions if f.name == func_name]
        
        if not matches:
            print(f"❌ 未找到函数: {func_name}")
            continue
        
        for i, func in enumerate(matches, 1):
            print(f"\n[{i}/{len(matches)}] {'🔧 函数定义' if not func.is_declaration else '🔗 函数声明'}: {func.name}")
            print(f"📁 文件: {Path(func.file_path).name}:{func.start_line}-{func.end_line}")
            print(f"🏷️  签名: {func.get_signature()}")
            
            print("=" * 60)
            body = func.get_body()
            if body:
                print(body)
            else:
                print("❌ 无法读取函数体内容")
            print("=" * 60)
        
        print("\n" + "-" * 80)


def test_detailed_parameter_info(analyzer: RepoAnalyzer):
    """测试功能3: 详细的参数和返回值信息"""
    print(f"\n🔬 测试功能3: 详细的参数和返回值信息")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    definitions = [f for f in functions if not f.is_declaration]
    
    print(f"📋 所有函数详细签名和参数信息 ({len(definitions)} 个函数定义):")
    print("=" * 100)
    
    for i, func in enumerate(definitions, 1):
        print(f"\n[{i:3}/{len(definitions)}] 🔧 函数: {func.name}")
        print("-" * 80)
        
        print(f"📝 详细签名: {func.get_detailed_signature()}")
        print(f"📁 位置: {func.file_path}:{func.start_line}-{func.end_line}")
        
        # 返回类型信息
        ret_info = func.return_type_details
        print(f"↩️  返回类型: {ret_info.get_type_signature()}")
        if ret_info.is_actually_pointer():
            print(f"   └─ {ret_info.get_pointer_analysis()}")
        
        # 参数信息
        if func.parameter_details:
            print(f"📋 参数列表 ({len(func.parameter_details)} 个):")
            for j, param in enumerate(func.parameter_details, 1):
                print(f"   {j:2}. {param.get_full_signature()}")
                if param.is_actually_pointer():
                    print(f"      └─ {param.get_pointer_analysis()}")
        else:
            print(f"📋 参数列表: 无参数")
    
    # 简单统计
    print(f"\n\n📊 简单统计:")
    print("=" * 80)
    
    total_params = sum(len(func.parameter_details) for func in definitions)
    pointer_params = sum(1 for func in definitions for param in func.parameter_details if param.is_actually_pointer())
    pointer_returns = sum(1 for func in definitions if func.return_type_details.is_actually_pointer())
    
    print(f"总函数定义: {len(definitions)}")
    print(f"总参数数: {total_params}")
    print(f"指针参数: {pointer_params} ({pointer_params/total_params*100:.1f}%)" if total_params > 0 else "指针参数: 0")
    print(f"返回指针的函数: {pointer_returns} ({pointer_returns/len(definitions)*100:.1f}%)")


def test_pointer_classification(analyzer: RepoAnalyzer):
    """测试功能4: 按指针参数和返回值数量分类函数"""
    print(f"\n🎯 测试功能4: 按指针参数和返回值数量分类函数")
    print("=" * 80)
    
    functions = analyzer.get_functions()
    definitions = [f for f in functions if not f.is_declaration]
    
    # 分类存储
    pointer_categories = {0: [], 1: [], 2: [], 3: []}
    
    # 对每个函数进行分类
    for func in definitions:
        pointer_param_count = sum(1 for param in func.parameter_details if param.is_actually_pointer())
        pointer_return_count = 1 if func.return_type_details.is_actually_pointer() else 0
        total_pointer_count = pointer_param_count + pointer_return_count
        
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
            pointer_params = [p for p in func.parameter_details if p.is_actually_pointer()]
            has_pointer_return = func.return_type_details.is_actually_pointer()
            
            print(f"   [{i:2}] {func.get_detailed_signature()}")
            print(f"        📁 {func.file_path}:{func.start_line}")
            
            # 显示指针详情
            pointer_details = []
            if has_pointer_return:
                pointer_details.append(f"返回值: {func.return_type_details.get_pointer_analysis()}")
            if pointer_params:
                param_analyses = [f"{p.name}({p.get_pointer_analysis()})" for p in pointer_params]
                pointer_details.append(f"参数: {', '.join(param_analyses)}")
            
            if pointer_details:
                print(f"        🎯 指针详情: {', '.join(pointer_details)}")
    
    # 简单分析
    pointer_counts = [len(pointer_categories[i]) for i in range(4)]
    max_pointers = max((func for funcs in pointer_categories.values() for func in funcs), 
                      key=lambda f: sum(1 for p in f.parameter_details if p.is_actually_pointer()) + 
                                   (1 if f.return_type_details.is_actually_pointer() else 0))
    max_pointer_count = sum(1 for p in max_pointers.parameter_details if p.is_actually_pointer()) + \
                       (1 if max_pointers.return_type_details.is_actually_pointer() else 0)
    
    print(f"\n📈 指针使用模式分析:")
    print("-" * 40)
    print(f"   指针最多的函数: {max_pointers.name} ({max_pointer_count}个指针)")
    print(f"   无指针函数占比: {len(pointer_categories[0])/len(definitions)*100:.1f}%")
    avg_pointers = sum(i * len(funcs) for i, funcs in enumerate(pointer_categories.items())) / len(definitions)
    print(f"   平均每个函数指针数: {avg_pointers:.2f}")


def test_library_analysis():
    """测试指定库的分析"""
    print("🚀 代码分析器测试")
    print("=" * 80)
    
    # 使用配置文件
    config_file = "test/miniz_config.json"
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return
    
    print("🧪 库文件分析测试")
    print("=" * 80)
    
    try:
        # 创建分析器
        analyzer = RepoAnalyzer(config_file)
        
        # 执行分析
        analyzer.analyze()
        
        # 运行测试
        # test_print_all_functions(analyzer)
        # test_print_function_body(analyzer)
        # test_detailed_parameter_info(analyzer)
        test_pointer_classification(analyzer)
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    try:
        test_library_analysis()
        
        print(f"\n🏁 测试完成")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 