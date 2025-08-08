#!/usr/bin/env python3
"""
测试CFG、CDG、DDG、PDG生成 - 分析test_functions.c中的每个函数
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser.repo_analyzer import RepoAnalyzer
from analysis import CFG, CDG, DDG, PDG
import logging

def extract_function_code(file_path, function_name, start_line, end_line):
    """从文件中提取指定函数的代码"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if start_line <= len(lines) and end_line <= len(lines):
            function_lines = lines[start_line-1:end_line]
            return ''.join(function_lines)
        else:
            return None
    except Exception as e:
        print(f"❌ 提取函数 {function_name} 代码失败: {e}")
        return None

def test_cfg_cdg_ddg_pdg():
    """测试CFG、CDG、DDG、PDG生成功能"""
    
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    
    # 获取测试文件路径
    # test_file = os.path.join(os.path.dirname(__file__), '/Users/shuangxiangkan/Tools/Slicer/benchmarks/utf8/utf8.h')
    # test_file = os.path.join(os.path.dirname(__file__), '/Users/shuangxiangkan/Tools/Slicer/benchmarks/cJSON/cJSON.c')
    test_file = os.path.join(os.path.dirname(__file__), "../benchmarks/configs/cjson_config.json")
    
    print("=" * 80)
    print("🔍 CFG/CDG/DDG/PDG 分析测试")
    print("=" * 80)
    print(f"📁 分析文件: {test_file}")
    print()
    
    try:
        # 1. 使用RepoAnalyzer提取函数信息
        print("🚀 第一步：提取函数信息...")
        analyzer = RepoAnalyzer(test_file)
        result = analyzer.analyze()
        
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return
        
        # 获取所有函数定义（排除声明）
        all_functions = analyzer.get_functions()
        function_definitions = [f for f in all_functions if not f.is_declaration]
        
        print(f"✅ 找到 {len(function_definitions)} 个函数定义")
        
        # 2. 为每个函数生成CFG、CDG、DDG、PDG
        print("\n🔬 第二步：生成各种图结构...")
        print("=" * 80)
        
        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(__file__), 'graph_outputs')
        os.makedirs(output_dir, exist_ok=True)
        
        # 按行号排序函数
        sorted_functions = sorted(function_definitions, key=lambda f: f.start_line)
        
        for i, func in enumerate(sorted_functions, 1):
            print(f"\n{'='*60}")
            print(f"🔸 函数 #{i}: {func.name}")
            print(f"📍 位置: 第 {func.start_line} - {func.end_line} 行")
            print(f"🔄 返回类型: {func.return_type}")
            print(f"📥 参数: {', '.join(func.parameters) if func.parameters else '无参数'}")
            print(f"{'='*60}")
            
            # 提取函数代码
            function_code = func.get_body()
            
            if not function_code:
                print(f"❌ 无法提取函数 {func.name} 的代码")
                continue
            
            print(f"📝 函数代码:")
            print("─" * 40)
            # 添加行号显示
            lines = function_code.strip().split('\n')
            for j, line in enumerate(lines, func.start_line):
                print(f"{j:3d}: {line}")
            print("─" * 40)
            
            # 生成CFG
            print(f"\n🌐 生成控制流图 (CFG)...")
            try:
                cfg_analyzer = CFG("c")
                cfg_output = os.path.join(output_dir, f"{func.name}_cfg")
                cfg_graph = cfg_analyzer.see_cfg(function_code, filename=cfg_output, pdf=True, view=False)
                
                if cfg_graph:
                    print(f"   ✅ CFG生成成功! 节点数: {len(cfg_graph.nodes)}, 边数: {sum(len(edges) for edges in cfg_graph.edges.values())}")
                    print(f"   📊 CFG已保存到: {cfg_output}.pdf")
                else:
                    print(f"   ❌ CFG生成失败")
                    
            except Exception as e:
                print(f"   ❌ CFG生成出错: {e}")
            
            # 生成CDG
            print(f"\n🎯 生成控制依赖图 (CDG)...")
            try:
                cdg_analyzer = CDG("c")
                cdg_output = os.path.join(output_dir, f"{func.name}_cdg")
                cdg_graph = cdg_analyzer.see_cdg(function_code, filename=cdg_output, pdf=True, view=False)
                
                if cdg_graph:
                    print(f"   ✅ CDG生成成功! 节点数: {len(cdg_graph.nodes)}, 边数: {sum(len(edges) for edges in cdg_graph.edges.values())}")
                    print(f"   📊 CDG已保存到: {cdg_output}.pdf")
                else:
                    print(f"   ❌ CDG生成失败")
                    
            except Exception as e:
                print(f"   ❌ CDG生成出错: {e}")
            
            # 生成DDG
            print(f"\n📊 生成数据依赖图 (DDG)...")
            try:
                ddg_analyzer = DDG("c")
                ddg_output = os.path.join(output_dir, f"{func.name}_ddg")
                ddg_graph = ddg_analyzer.see_ddg(function_code, filename=ddg_output, pdf=True, view=False)
                
                if ddg_graph:
                    print(f"   ✅ DDG生成成功! 节点数: {len(ddg_graph.nodes)}, 边数: {sum(len(edges) for edges in ddg_graph.edges.values())}")
                    print(f"   📊 DDG已保存到: {ddg_output}.pdf")
                else:
                    print(f"   ❌ DDG生成失败")
                    
            except Exception as e:
                print(f"   ❌ DDG生成出错: {e}")
            
            # 生成PDG
            print(f"\n🔗 生成程序依赖图 (PDG)...")
            try:
                pdg_analyzer = PDG("c")
                pdg_output = os.path.join(output_dir, f"{func.name}_pdg")
                pdg_graph = pdg_analyzer.see_pdg(function_code, filename=pdg_output, pdf=True, view=False)
                
                if pdg_graph:
                    print(f"   ✅ PDG生成成功! 节点数: {len(pdg_graph.nodes)}, 边数: {sum(len(edges) for edges in pdg_graph.edges.values())}")
                    print(f"   📊 PDG已保存到: {pdg_output}.pdf")
                else:
                    print(f"   ❌ PDG生成失败")
                    
            except Exception as e:
                print(f"   ❌ PDG生成出错: {e}")
        
        # 打印总结信息
        print(f"\n{'='*80}")
        print(f"📊 总结信息:")
        print(f"   处理函数总数: {len(sorted_functions)}")
        print(f"   输出目录: {output_dir}")
        print(f"   生成的图文件: {func.name}_{{cfg|cdg|ddg|pdg}}.pdf")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_cfg_cdg_ddg_pdg()
    
    print("\n" + "=" * 80)
    print("✅ CFG/CDG/DDG/PDG 测试完成!")
    print("=" * 80)