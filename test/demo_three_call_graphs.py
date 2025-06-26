#!/usr/bin/env python3
"""
演示三种Call Graph的生成和使用
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer
from graph.call_graph_generator import CallGraphGenerator


def demo_three_call_graphs():
    """演示三种Call Graph的生成"""
    
    print("🎯 Call Graph 三种模式演示")
    print("=" * 50)
    
    # 初始化分析器
    analyzer = RepoAnalyzer("test/miniz_config.json")
    analyzer.analyze("libraries/miniz")
    generator = CallGraphGenerator(analyzer)
    
    # 演示函数
    func_name = "mz_compress2"
    
    print(f"📍 分析函数: {func_name}")
    print("-" * 30)
    
    # 显示函数的调用统计
    callees = analyzer.get_direct_callees(func_name)
    callers = analyzer.get_direct_callers(func_name)
    
    print(f"直接调用关系:")
    print(f"  • {func_name} 调用 {len(callees)} 个函数: {', '.join(sorted(callees))}")
    print(f"  • {func_name} 被 {len(callers)} 个函数调用: {', '.join(sorted(callers))}")
    print()
    
    # 生成三种Call Graph
    print("🔗 生成三种Call Graph:")
    print("-" * 30)
    
    # 1. Callees图 - 显示该函数调用的所有函数
    success = generator.generate_function_callees_graph(
        func_name, f"test/{func_name}_callees.dot"
    )
    if success:
        print(f"1️⃣  Callees图: test/{func_name}_callees.dot")
        print(f"   显示 {func_name} 调用的所有函数（直接+间接）")
    
    # 2. Callers图 - 显示调用该函数的所有函数
    success = generator.generate_function_callers_graph(
        func_name, f"test/{func_name}_callers.dot"
    )
    if success:
        print(f"2️⃣  Callers图: test/{func_name}_callers.dot")
        print(f"   显示调用 {func_name} 的所有函数（直接+间接）")
    
    # 3. 完整图 - 显示所有相关函数
    success = generator.generate_function_call_graph(
        func_name, f"test/{func_name}_complete.dot"
    )
    if success:
        print(f"3️⃣  完整图: test/{func_name}_complete.dot")
        print(f"   显示 {func_name} 的完整调用关系（callers + callees）")
    
    print("\n💡 使用场景:")
    print("-" * 30)
    print("📈 Callees图 - 了解函数的复杂度和依赖关系")
    print("📊 Callers图 - 了解函数的重要性和影响范围") 
    print("🔄 完整图 - 全面了解函数在系统中的位置")
    
    print("\n🎨 可视化命令:")
    print("-" * 30)
    print(f"dot -Tpng test/{func_name}_callees.dot -o test/{func_name}_callees.png")
    print(f"dot -Tpng test/{func_name}_callers.dot -o test/{func_name}_callers.png")
    print(f"dot -Tpng test/{func_name}_complete.dot -o test/{func_name}_complete.png")


if __name__ == "__main__":
    demo_three_call_graphs() 