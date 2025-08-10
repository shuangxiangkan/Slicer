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
    # test_file = os.path.join(os.path.dirname(__file__), "../benchmarks/configs/cjson_config.json")
    # test_file = os.path.join(os.path.dirname(__file__), "../benchmarks/configs/miniz_config.json")
    test_file = os.path.join(os.path.dirname(__file__), "test_functions.c")
    
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
        
        # 初始化统计计数器
        stats = {
            'CFG': {'success': 0, 'failure': 0},
            'CDG': {'success': 0, 'failure': 0},
            'DDG': {'success': 0, 'failure': 0},
            'PDG': {'success': 0, 'failure': 0}
        }
        
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
                    stats['CFG']['success'] += 1
                    print(f"   ✅ CFG生成成功! 节点数: {len(cfg_graph.nodes)}, 边数: {len(cfg_graph.edges)}")
                    print(f"   📊 CFG已保存到: {cfg_output}.pdf")
                    
                    # 打印CFG边信息
                    print(f"   🔍 CFG边信息:")
                    if cfg_graph.edges:
                        for i, edge in enumerate(cfg_graph.edges, 1):
                            source_text = edge.source_node.text.strip()[:30] + "..." if len(edge.source_node.text.strip()) > 30 else edge.source_node.text.strip()
                            target_text = edge.target_node.text.strip()[:30] + "..." if len(edge.target_node.text.strip()) > 30 else edge.target_node.text.strip()
                            label = edge.label if hasattr(edge, 'label') and edge.label else "(无Label)"
                            print(f"     📍 边 #{i}: 节点{edge.source_node.id} -> 节点{edge.target_node.id}")
                            print(f"        Source: {source_text}")
                            print(f"        Target: {target_text}")
                            print(f"        Label: {label}")
                    else:
                        print(f"     ℹ️  该函数没有CFG边")
                else:
                    stats['CFG']['failure'] += 1
                    print(f"   ❌ CFG生成失败")
                    
            except Exception as e:
                stats['CFG']['failure'] += 1
                print(f"   ❌ CFG生成出错: {e}")
            
            # 生成CDG
            print(f"\n🎯 生成控制依赖图 (CDG)...")
            try:
                cdg_analyzer = CDG("c")
                cdg_output = os.path.join(output_dir, f"{func.name}_cdg")
                cdg_graph = cdg_analyzer.see_cdg(function_code, filename=cdg_output, pdf=True, view=False)
                
                if cdg_graph:
                    stats['CDG']['success'] += 1
                    print(f"   ✅ CDG生成成功! 节点数: {len(cdg_graph.nodes)}, 边数: {len(cdg_graph.edges)}")
                    print(f"   📊 CDG已保存到: {cdg_output}.pdf")
                    
                    # 打印CDG边信息
                    print(f"   🔍 CDG边信息:")
                    if cdg_graph.edges:
                        for i, edge in enumerate(cdg_graph.edges, 1):
                            source_text = edge.source_node.text.strip()[:30] + "..." if len(edge.source_node.text.strip()) > 30 else edge.source_node.text.strip()
                            target_text = edge.target_node.text.strip()[:30] + "..." if len(edge.target_node.text.strip()) > 30 else edge.target_node.text.strip()
                            label = edge.label if hasattr(edge, 'label') and edge.label else "(无Label)"
                            print(f"     📍 边 #{i}: 节点{edge.source_node.id} -> 节点{edge.target_node.id}")
                            print(f"        Source: {source_text}")
                            print(f"        Target: {target_text}")
                            print(f"        Label: {label}")
                    else:
                        print(f"     ℹ️  该函数没有CDG边")
                else:
                    stats['CDG']['failure'] += 1
                    print(f"   ❌ CDG生成失败")
                    
            except Exception as e:
                stats['CDG']['failure'] += 1
                print(f"   ❌ CDG生成出错: {e}")
            
            # 生成DDG
            print(f"\n📊 生成数据依赖图 (DDG)...")
            try:
                ddg_analyzer = DDG("c")
                ddg_output = os.path.join(output_dir, f"{func.name}_ddg")
                ddg_graph = ddg_analyzer.see_ddg(function_code, filename=ddg_output, pdf=True, view=False)
                
                if ddg_graph:
                    stats['DDG']['success'] += 1
                    print(f"   ✅ DDG生成成功! 节点数: {len(ddg_graph.nodes)}, 边数: {len(ddg_graph.edges)}")
                    print(f"   📊 DDG已保存到: {ddg_output}.pdf")
                    
                    # 打印DDG边信息
                    print(f"   🔍 DDG边信息:")
                    if ddg_graph.edges:
                        for i, edge in enumerate(ddg_graph.edges, 1):
                            source_text = edge.source_node.text.strip()[:30] + "..." if len(edge.source_node.text.strip()) > 30 else edge.source_node.text.strip()
                            target_text = edge.target_node.text.strip()[:30] + "..." if len(edge.target_node.text.strip()) > 30 else edge.target_node.text.strip()
                            label = edge.label if hasattr(edge, 'label') and edge.label else "(无Label)"
                            variables = edge.variables if hasattr(edge, 'variables') else (edge.token if hasattr(edge, 'token') else [])
                            var_info = f", 依赖变量: {', '.join(variables)}" if variables else ""
                            print(f"     📍 边 #{i}: 节点{edge.source_node.id} -> 节点{edge.target_node.id}")
                            print(f"        Source: {source_text}")
                            print(f"        Target: {target_text}")
                            print(f"        Label: {label}{var_info}")
                    else:
                        print(f"     ℹ️  该函数没有DDG边")
                else:
                    stats['DDG']['failure'] += 1
                    print(f"   ❌ DDG生成失败")
                    
            except Exception as e:
                stats['DDG']['failure'] += 1
                print(f"   ❌ DDG生成出错: {e}")
            
            # 生成PDG
            print(f"\n🔗 生成程序依赖图 (PDG)...")
            try:
                pdg_analyzer = PDG("c")
                pdg_output = os.path.join(output_dir, f"{func.name}_pdg")
                pdg_graph = pdg_analyzer.see_pdg(function_code, filename=pdg_output, pdf=True, view=False)
                
                if pdg_graph:
                    stats['PDG']['success'] += 1
                    print(f"   ✅ PDG生成成功! 节点数: {len(pdg_graph.nodes)}, 边数: {len(pdg_graph.edges)}")
                    print(f"   📊 PDG已保存到: {pdg_output}.pdf")
                    
                    # 打印PDG边信息
                    print(f"   🔍 PDG边信息:")
                    if pdg_graph.edges:
                        # 按边类型分组显示
                        cfg_edges = [e for e in pdg_graph.edges if hasattr(e, 'type') and e.type == 'CFG']
                        cdg_edges = [e for e in pdg_graph.edges if hasattr(e, 'type') and e.type == 'CDG']
                        ddg_edges = [e for e in pdg_graph.edges if hasattr(e, 'type') and e.type == 'DDG']
                        other_edges = [e for e in pdg_graph.edges if not hasattr(e, 'type') or e.type not in ['CFG', 'CDG', 'DDG']]
                        
                        edge_count = 0
                        for edge_type, edges in [('CFG', cfg_edges), ('CDG', cdg_edges), ('DDG', ddg_edges), ('其他', other_edges)]:
                            if edges:
                                print(f"     🏷️  {edge_type}边 ({len(edges)}条):")
                                for edge in edges:
                                    edge_count += 1
                                    source_text = edge.source_node.text.strip()[:30] + "..." if len(edge.source_node.text.strip()) > 30 else edge.source_node.text.strip()
                                    target_text = edge.target_node.text.strip()[:30] + "..." if len(edge.target_node.text.strip()) > 30 else edge.target_node.text.strip()
                                    label = edge.label if hasattr(edge, 'label') and edge.label else "(无Label)"
                                    variables = edge.variables if hasattr(edge, 'variables') else (edge.token if hasattr(edge, 'token') else [])
                                    var_info = f", 依赖变量: {', '.join(variables)}" if variables else ""
                                    print(f"        📍 边 #{edge_count}: 节点{edge.source_node.id} -> 节点{edge.target_node.id}")
                                    print(f"           Source: {source_text}")
                                    print(f"           Target: {target_text}")
                                    print(f"           Label: {label}{var_info}")
                    else:
                        print(f"     ℹ️  该函数没有PDG边")
                else:
                    stats['PDG']['failure'] += 1
                    print(f"   ❌ PDG生成失败")
                    
            except Exception as e:
                stats['PDG']['failure'] += 1
                print(f"   ❌ PDG生成出错: {e}")
        
        # 打印总结信息
        print(f"\n{'='*80}")
        print(f"📊 总结信息:")
        print(f"   处理函数总数: {len(sorted_functions)}")
        print(f"   输出目录: {output_dir}")
        print(f"   生成的图文件: {{函数名}}_{{cfg|cdg|ddg|pdg}}.pdf")
        print(f"{'='*80}")
        
        # 打印详细统计信息
        print(f"\n📈 图生成统计:")
        print(f"{'='*80}")
        total_success = 0
        total_failure = 0
        
        for graph_type in ['CFG', 'CDG', 'DDG', 'PDG']:
            success = stats[graph_type]['success']
            failure = stats[graph_type]['failure']
            total = success + failure
            success_rate = (success / total * 100) if total > 0 else 0
            
            total_success += success
            total_failure += failure
            
            print(f"🔸 {graph_type}:")
            print(f"   ✅ 成功: {success} 个")
            print(f"   ❌ 失败: {failure} 个")
            print(f"   📊 成功率: {success_rate:.1f}%")
            print()
        
        # 总体统计
        total_graphs = total_success + total_failure
        overall_success_rate = (total_success / total_graphs * 100) if total_graphs > 0 else 0
        
        print(f"🎯 总体统计:")
        print(f"   📊 总图数: {total_graphs} 个")
        print(f"   ✅ 总成功: {total_success} 个")
        print(f"   ❌ 总失败: {total_failure} 个")
        print(f"   🏆 总成功率: {overall_success_rate:.1f}%")
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
