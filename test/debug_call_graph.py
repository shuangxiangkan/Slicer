#!/usr/bin/env python3
"""
调试Call Graph
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer


def debug_call_graph():
    """调试Call Graph"""
    analyzer = RepoAnalyzer("test/miniz_config.json")
    analyzer.analyze()
    
    call_graph = analyzer.get_call_graph()
    
    print("🔍 调试Call Graph内部状态:")
    print(f"总函数数: {len(call_graph.functions)}")
    print(f"Call Graph是否已构建: {call_graph._graph_built}")
    
    print(f"\n📞 所有调用关系 (call_graph):")
    for caller, callees in call_graph.call_graph.items():
        if callees:
            print(f"  {caller} -> {sorted(callees)}")
    
    print(f"\n📲 所有被调用关系 (reverse_call_graph):")
    for callee, callers in call_graph.reverse_call_graph.items():
        if callers:
            print(f"  {callee} <- {sorted(callers)}")
    
    # 专门检查mz_compress2
    print(f"\n🔍 专门检查 mz_compress2:")
    func_name = "mz_compress2"
    
    if func_name in call_graph.functions:
        func_info = call_graph.functions[func_name]
        print(f"  函数对象存在: {func_info}")
        print(f"  是否声明: {func_info.is_declaration}")
        print(f"  已解析调用: {func_info._parsed_calls}")
        print(f"  调用的函数: {func_info.callees}")
    else:
        print(f"  ❌ 函数 {func_name} 不在Call Graph中")
    
    # 检查Call Graph中的调用关系
    direct_callees = analyzer.get_direct_callees(func_name)
    print(f"  通过API获取的直接调用: {direct_callees}")
    
    # 检查原始的call_graph数据结构
    if func_name in call_graph.call_graph:
        print(f"  call_graph中的调用关系: {call_graph.call_graph[func_name]}")
    else:
        print(f"  ❌ {func_name} 不在call_graph中")


if __name__ == "__main__":
    debug_call_graph() 