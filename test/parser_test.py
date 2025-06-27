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
from graph.call_graph_generator import CallGraphGenerator


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
    test_functions = ["mz_compress2"]
    
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


def test_call_graph_analysis(analyzer: RepoAnalyzer):
    """测试功能5: Call Graph分析"""
    print(f"\n🔗 测试功能5: Call Graph分析")
    print("=" * 80)
    
    # 测试几个具体的函数
    # test_functions = ["mz_compress2", "mz_deflateInit", "mz_uncompress2"]
    test_functions = ["cJSON_ParseWithLengthOpts"]
    
    for func_name in test_functions:
        print(f"\n🔍 分析函数: {func_name}")
        print("-" * 60)
        
        # 直接调用的函数
        direct_callees = analyzer.get_direct_callees(func_name)
        if direct_callees:
            print(f"📞 直接调用 ({len(direct_callees)} 个):")
            for callee in sorted(direct_callees):
                print(f"   └─ {callee}")
        else:
            print(f"📞 直接调用: 无")
        
        # 被哪些函数直接调用
        direct_callers = analyzer.get_direct_callers(func_name)
        if direct_callers:
            print(f"📲 被直接调用 ({len(direct_callers)} 个):")
            for caller in sorted(direct_callers):
                print(f"   └─ {caller}")
        else:
            print(f"📲 被直接调用: 无")
        
        # 所有callees（直接和间接依赖）- 无深度限制，显示全部
        all_deps = analyzer.get_function_dependencies(func_name, max_depth=None)
        if all_deps:
            print(f"🌳 所有Callees (直接+间接, {len(all_deps)} 个):")
            
            # 按深度分组显示
            deps_by_depth = {}
            for dep, depth in all_deps.items():
                if depth not in deps_by_depth:
                    deps_by_depth[depth] = []
                deps_by_depth[depth].append(dep)
            
            # 显示每个深度的全部依赖
            for depth in sorted(deps_by_depth.keys()):
                deps = sorted(deps_by_depth[depth])
                print(f"   深度{depth} ({len(deps)}个): ", end="")
                
                # 按行显示，每行最多显示6个函数名
                for i, dep in enumerate(deps):
                    if i > 0 and i % 6 == 0:
                        print(f"\n   {'':>12}", end="")
                    print(f"{dep}", end="")
                    if i < len(deps) - 1:
                        print(", ", end="")
                print()  # 换行
                
            # 显示总体统计
            print(f"   📊 统计: 总计{len(all_deps)}个函数，最大深度{max(all_deps.values())}")
            
            # 按字母顺序显示所有callees（便于查找）
            print(f"   📝 按字母顺序: ", end="")
            all_callees_sorted = sorted(all_deps.keys())
            for i, callee in enumerate(all_callees_sorted):
                if i > 0 and i % 8 == 0:
                    print(f"\n   {'':>17}", end="")
                print(f"{callee}", end="")
                if i < len(all_callees_sorted) - 1:
                    print(", ", end="")
            print()  # 换行
        else:
            print(f"🌳 所有Callees: 无")
        
        print()
    
    # 显示Call Graph全局统计
    print(f"\n📊 Call Graph全局统计:")
    print("=" * 60)
    
    summary = analyzer.get_call_graph_summary()
    print(f"总函数数: {summary['total_functions']}")
    print(f"调用关系数: {summary['total_call_edges']}")
    print(f"外部依赖数: {summary['external_dependencies']}")
    print(f"平均每函数调用数: {summary['avg_callees_per_function']:.2f}")
    print(f"叶子函数数: {summary['leaf_functions_count']} ({summary['leaf_functions_count']/summary['total_functions']*100:.1f}%)")
    print(f"根函数数: {summary['root_functions_count']} ({summary['root_functions_count']/summary['total_functions']*100:.1f}%)")
    
    # 显示循环依赖
    cycles = analyzer.find_cycles()
    if cycles:
        print(f"\n⚠️  发现循环依赖 ({len(cycles)} 个):")
        for i, cycle in enumerate(cycles, 1):
            print(f"   {i}. {' → '.join(cycle)}")
    else:
        print(f"\n✅ 无循环依赖")
    
    # 显示外部依赖
    external_deps = analyzer.get_external_dependencies()
    if external_deps:
        print(f"\n🔗 外部依赖 ({len(external_deps)} 个):")
        sorted_deps = sorted(external_deps)
        # 只显示前10个
        for dep in sorted_deps[:10]:
            print(f"   └─ {dep}")
        if len(sorted_deps) > 10:
            print(f"   └─ ... 还有 {len(sorted_deps) - 10} 个")
    else:
        print(f"\n🔗 外部依赖: 无")


def test_dot_graph_generation(analyzer: RepoAnalyzer):
    """测试功能6: DOT图生成"""
    print(f"\n📊 测试功能6: DOT图生成")
    print("=" * 80)
    
    # 创建图生成器
    generator = CallGraphGenerator(analyzer)
    
    # 生成整个仓库的Call Graph
    print("🔗 生成整个仓库Call Graph...")
    success = generator.generate_repo_call_graph("test/repo_call_graph.dot")
    if success:
        print("   ✅ 已生成: test/repo_call_graph.dot")
    else:
        print("   ❌ 生成失败")
    
    # 生成特定函数的三种Call Graph
    test_function = "mz_compress2"
    
    print(f"📍 生成函数 {test_function} 的三种Call Graph...")
    
    # 生成callees图
    success = generator.generate_function_callees_graph(
        func_name=test_function,
        output_file=f"test/{test_function}_callees.dot"
    )
    if success:
        print(f"   ✅ Callees图: test/{test_function}_callees.dot")
    else:
        print(f"   ❌ Callees图生成失败")
    
    # 生成callers图
    success = generator.generate_function_callers_graph(
        func_name=test_function,
        output_file=f"test/{test_function}_callers.dot"
    )
    if success:
        print(f"   ✅ Callers图: test/{test_function}_callers.dot")
    else:
        print(f"   ❌ Callers图生成失败")
    
    # 生成完整图
    success = generator.generate_function_call_graph(
        func_name=test_function,
        output_file=f"test/{test_function}_complete.dot"
    )
    if success:
        print(f"   ✅ 完整图: test/{test_function}_complete.dot")
    else:
        print(f"   ❌ 完整图生成失败")
    
    print("\n💡 提示:")
    print("   查看DOT文件: cat test/repo_call_graph.dot")
    print("   转换为图片: dot -Tpng test/repo_call_graph.dot -o test/repo_call_graph.png")
    print("   在线查看: https://dreampuf.github.io/GraphvizOnline/")


def test_library_analysis():
    """测试指定库的分析"""
    print("🚀 代码分析器测试")
    print("=" * 80)
    
    # 使用配置文件
    config_file = "test/cjson_config.json"
    
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
        # test_pointer_classification(analyzer)
        test_call_graph_analysis(analyzer)
        # test_dot_graph_generation(analyzer)
        
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