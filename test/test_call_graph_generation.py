#!/usr/bin/env python3
"""
简化的DOT图生成测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer
from parser.call_graph_generator import CallGraphGenerator


def test_simple_dot_generation():
    """测试简化的Call Graph DOT生成"""
    
    print("🎨 简化的Call Graph DOT文件生成测试")
    print("=" * 60)
    
    try:
        # 使用现有的配置文件分析cjson库
        # analyzer = RepoAnalyzer("test/cjson_config.json")
        analyzer = RepoAnalyzer("benchmarks/configs/zlib_config.json")
        
        print("📁 分析miniz库...")
        analyzer.analyze()
        
        # 创建图生成器
        generator = CallGraphGenerator(analyzer)
        
        print("\n🔗 生成DOT文件...")
        print("-" * 30)
        
        # 1. 生成整个仓库的Call Graph
        print("1. 生成整个仓库Call Graph...")
        success = generator.generate_repo_call_graph("test/repo_call_graph.dot")
        if success:
            print("   ✅ 已生成: test/repo_call_graph.dot")
        else:
            print("   ❌ 生成失败")
        
        # 2. 生成几个关键函数的三种Call Graph
        # test_functions = ["mz_compress2", "mz_uncompress2"]
        test_functions = ["compress"]
        
        for func_name in test_functions:
            print(f"\n2. 生成函数 {func_name} 的三种Call Graph...")
            
            # 2.1 只显示callees（该函数调用的所有函数）
            success = generator.generate_function_callees_graph(
                func_name=func_name,
                output_file=f"test/{func_name}_callees.dot"
            )
            if success:
                print(f"   ✅ Callees图: test/{func_name}_callees.dot")
            else:
                print(f"   ❌ Callees图生成失败")
            
            # 2.2 只显示callers（调用该函数的所有函数）
            success = generator.generate_function_callers_graph(
                func_name=func_name,
                output_file=f"test/{func_name}_callers.dot"
            )
            if success:
                print(f"   ✅ Callers图: test/{func_name}_callers.dot")
            else:
                print(f"   ❌ Callers图生成失败")
            
            # 2.3 完整图（包含callers和callees）
            success = generator.generate_function_call_graph(
                func_name=func_name,
                output_file=f"test/{func_name}_complete.dot"
            )
            if success:
                print(f"   ✅ 完整图: test/{func_name}_complete.dot")
            else:
                print(f"   ❌ 完整图生成失败")
        
        print(f"\n📊 生成完成！")
        print("-" * 30)
        print("💡 查看DOT文件:")
        print("   - 仓库图: cat test/repo_call_graph.dot")
        print("   - 函数callees: cat test/compress_callees.dot")
        print("   - 函数callers: cat test/compress_callers.dot")
        print("   - 函数完整图: cat test/compress_complete.dot")
        print("\n   转换为图片:")
        print("   - dot -Tpng test/compress_callees.dot -o test/compress_callees.png")
        print("   - dot -Tpng test/compress_callers.dot -o test/compress_callers.png")
        print("   - dot -Tpng test/compress_complete.dot -o test/compress_complete.png")
        print("\n   在线查看: https://dreampuf.github.io/GraphvizOnline/")
        print("\n✅ DOT修复说明:")
        print("   - 移除HTML标签，简化函数签名显示")
        print("   - 添加字符转义，确保特殊字符正确处理")
        print("   - 限制参数长度，避免节点过大")
        print("   - 现在生成的DOT文件可以正常被Graphviz渲染")
        
        print(f"\n🔍 验证Call Graph正确性:")
        print("-" * 30)
        
        # 输出一些关键函数的调用关系供验证
        key_checks = [
            "compress"
            # "cJSON_ParseWithOpts"
        ]
        
        for func_name in key_checks:
            functions = generator.call_graph.functions
            if func_name in functions:
                callees = analyzer.get_direct_callees(func_name)
                callers = analyzer.get_direct_callers(func_name)
                print(f"• {func_name}:")
                print(f"  - 调用 {len(callees)} 个函数: {', '.join(sorted(callees))}")
                print(f"  - 被 {len(callers)} 个函数调用: {', '.join(sorted(callers))}")
            else:
                print(f"• {func_name}: 未找到")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_simple_dot_generation() 