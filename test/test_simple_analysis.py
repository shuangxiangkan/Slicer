#!/usr/bin/env python3
"""
测试简单函数的CFG/DDG/PDG分析
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analysis import CFG, DDG, PDG
from parser import RepoAnalyzer


def analyze_function_from_file(function_name: str):
    """从test_functions.c文件中解析并分析指定函数"""

    print(f"🔍 测试函数: {function_name}")
    print("=" * 50)

    # 创建配置文件
    config_content = {
        "library_path": os.path.abspath("test"),
        "include_files": ["test_functions.c"],
        "exclude_files": []
    }

    config_file = "test/test_config.json"
    import json
    with open(config_file, 'w') as f:
        json.dump(config_content, f, indent=2)

    try:
        # 使用RepoAnalyzer分析C文件
        print("🔧 初始化RepoAnalyzer...")
        analyzer = RepoAnalyzer(config_file)

        print("📊 分析test_functions.c文件...")
        result = analyzer.analyze()
        print(f"✅ 分析完成，总共找到 {result['total_functions']} 个函数")

        # 获取所有函数
        functions = analyzer.get_functions()
        print(f"📋 找到的函数: {[f.name for f in functions if not f.is_declaration]}")

        # 查找目标函数 - 通过函数体内容匹配，因为函数名解析有问题
        target_func = None
        function_mapping = {
            "add": "int add(int a, int b)",
            "max": "int max(int a, int b)",
            "sum": "int sum(int n)",
            "factorial": "int factorial(int n)",
            "fibonacci": "int fibonacci(int n)",
            "grade_to_points": "int grade_to_points(char grade)",
            "array_sum": "int array_sum(int arr[], int size)"
        }

        expected_signature = function_mapping.get(function_name, "")

        for func in functions:
            if not func.is_declaration:
                body = func.get_body()
                if body and expected_signature in body:
                    target_func = func
                    break

        if not target_func:
            print(f"❌ 未找到函数: {function_name}")
            print(f"期望签名: {expected_signature}")
            return False

        print(f"✅ 找到目标函数: {function_name}")
        print(f"📁 文件: {os.path.basename(target_func.file_path)}")
        print(f"📍 行号: {target_func.start_line}-{target_func.end_line}")

        # 获取函数体
        function_body = target_func.get_body()
        if not function_body:
            print("❌ 无法获取函数体")
            return False

        print(f"📖 函数体:")
        print(function_body)

        # 创建输出目录
        os.makedirs('test/simple_output', exist_ok=True)

        # CFG分析
        print("\n📈 CFG分析:")
        cfg = CFG('c')
        cfg_graphs = cfg.see_cfg(function_body, filename=f'test/simple_output/{function_name}_cfg',
                                pdf=True, dot_format=True, view=False)
        if cfg_graphs and len(cfg_graphs) > 0:
            print(f"✅ CFG构建完成，{len(cfg_graphs[0].nodes)} 个节点")
        else:
            print("❌ CFG构建失败")
            return False

        # DDG分析
        print("📊 DDG分析:")
        ddg = DDG('c')
        ddg_graphs = ddg.see_ddg(function_body, filename=f'test/simple_output/{function_name}_ddg',
                                pdf=True, dot_format=True, view=False)
        deps = ddg.get_data_dependencies(function_body)
        if deps and len(deps) > 0:
            print(f"✅ DDG构建完成，{len(deps[0]['dependencies'])} 个数据依赖")
            # 显示一些数据依赖示例
            if len(deps[0]['dependencies']) > 0:
                print("🔍 数据依赖示例:")
                for i, dep in enumerate(deps[0]['dependencies'][:3]):
                    print(f"  {i+1}. 行{dep['source']['line']} -> 行{dep['target']['line']}: {dep['variables']}")
        else:
            print("✅ DDG构建完成，0 个数据依赖")

        # PDG分析
        print("🔗 PDG分析:")
        pdg = PDG('c')
        pdg_graphs = pdg.see_pdg(function_body, filename=f'test/simple_output/{function_name}_pdg',
                                pdf=True, dot_format=True, view=False)
        complexity = pdg.analyze_function_complexity(function_body)
        if complexity:
            print(f"✅ PDG构建完成，{complexity['total_dependencies']} 个总依赖")
        else:
            print("❌ PDG构建失败")

        return True

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理配置文件
        if os.path.exists(config_file):
            os.remove(config_file)


def main():
    """主测试函数"""
    print("🚀 开始简单函数CFG/DDG/PDG分析测试")
    print("📁 C文件: test/test_functions.c")
    print("📁 输出目录: test/simple_output/")
    print("📊 生成格式: .dot 和 .pdf")
    print()

    # 检查C文件是否存在
    if not os.path.exists("test/test_functions.c"):
        print("❌ test/test_functions.c 文件不存在")
        return

    test_results = []

    # 从test_functions.c中解析的函数名列表
    test_function_names = [
        "add",
        "max",
        "sum",
        "factorial",
        "fibonacci",
        "grade_to_points",
        "array_sum"
    ]

    for function_name in test_function_names:
        try:
            success = analyze_function_from_file(function_name)
            test_results.append((function_name, success))
            print(f"{'✅' if success else '❌'} {function_name}函数分析{'成功' if success else '失败'}")
        except Exception as e:
            print(f"❌ {function_name}函数分析异常: {e}")
            test_results.append((function_name, False))

    # 输出总结
    print("\n" + "="*50)
    print("📊 简单函数分析测试总结")
    print("="*50)

    success_count = sum(1 for _, success in test_results if success)
    total_count = len(test_results)

    for function_name, success in test_results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {function_name:15s}: {status}")

    print(f"\n总体结果: {success_count}/{total_count} 个函数分析成功")

    if success_count == total_count:
        print("🎉 所有函数分析测试通过！")
        print("📁 查看 test/simple_output/ 目录获取详细结果")
        print("📊 每个函数都生成了CFG、DDG、PDG的.dot和.pdf文件")
        print("\n💡 文件说明:")
        print("1. .dot文件: Graphviz源码，可用于进一步处理")
        print("2. .pdf文件: 可视化图形，可直接查看")
        print("3. CFG显示控制流结构")
        print("4. DDG显示数据依赖关系（红色虚线）")
        print("5. PDG结合控制依赖和数据依赖")
    elif success_count > 0:
        print("⚠️  部分函数分析成功")
        print("📁 查看 test/simple_output/ 目录获取详细结果")
    else:
        print("💥 所有函数分析失败")


if __name__ == "__main__":
    main()
