#!/usr/bin/env python3
"""
对比测试结果 - 验证修改前后的图构建结果是否一致

用法:
    python compare_results.py                    # 对比所有测试程序
    python compare_results.py --program 01      # 只对比指定编号的程序
    python compare_results.py --graph ddg       # 只对比指定类型的图
    python compare_results.py --verbose         # 显示详细差异
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from analysis import CFG, CDG, DDG, PDG
from build_baseline import GraphToJSON


class ResultComparator:
    """结果对比器"""
    
    def __init__(self, test_programs_dir, expected_results_dir, verbose=False):
        self.test_programs_dir = Path(test_programs_dir)
        self.expected_results_dir = Path(expected_results_dir)
        self.verbose = verbose
    
    def load_baseline(self, program_name):
        """加载基准结果"""
        baseline_file = self.expected_results_dir / f"{program_name}.json"
        if not baseline_file.exists():
            return None
        
        with open(baseline_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def read_code(self, program_file):
        """读取C代码"""
        with open(program_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def build_current_graph(self, code, graph_type):
        """构建当前版本的图"""
        if graph_type == 'cfg':
            builder = CFG("c")
            return builder.construct_cfg(code)
        elif graph_type == 'cdg':
            builder = CDG("c")
            return builder.construct_cdg(code)
        elif graph_type == 'ddg':
            builder = DDG("c")
            return builder.construct_ddg(code)
        elif graph_type == 'pdg':
            builder = PDG("c")
            return builder.construct_pdg(code)
        else:
            return None
    
    def compare_nodes(self, nodes1: List[Dict], nodes2: List[Dict]) -> Tuple[bool, List[str]]:
        """对比节点列表"""
        diffs = []
        
        if len(nodes1) != len(nodes2):
            diffs.append(f"节点数量不同: 基准={len(nodes1)}, 当前={len(nodes2)}")
            return False, diffs
        
        # 构建节点映射（按ID）
        nodes1_map = {n['id']: n for n in nodes1}
        nodes2_map = {n['id']: n for n in nodes2}
        
        # 检查每个节点
        for node_id in nodes1_map:
            if node_id not in nodes2_map:
                diffs.append(f"节点ID {node_id} 在当前结果中缺失")
                continue
            
            n1 = nodes1_map[node_id]
            n2 = nodes2_map[node_id]
            
            # 对比关键属性
            if n1['text'] != n2['text']:
                diffs.append(f"节点{node_id}文本不同: '{n1['text'][:30]}...' vs '{n2['text'][:30]}...'")
            
            if set(n1['defs']) != set(n2['defs']):
                diffs.append(f"节点{node_id} defs不同: {n1['defs']} vs {n2['defs']}")
            
            if set(n1['uses']) != set(n2['uses']):
                diffs.append(f"节点{node_id} uses不同: {n1['uses']} vs {n2['uses']}")
        
        return len(diffs) == 0, diffs
    
    def compare_edges(self, edges1: List[Dict], edges2: List[Dict]) -> Tuple[bool, List[str]]:
        """对比边列表"""
        diffs = []
        
        if len(edges1) != len(edges2):
            diffs.append(f"边数量不同: 基准={len(edges1)}, 当前={len(edges2)}")
            # 继续比较，看看具体差异
        
        # 构建边的集合（用于快速查找）
        def edge_key(e):
            key = (e['source_id'], e['target_id'])
            if 'variables' in e:
                key += (tuple(sorted(e['variables'])),)
            return key
        
        edges1_set = {edge_key(e): e for e in edges1}
        edges2_set = {edge_key(e): e for e in edges2}
        
        # 找出缺失的边
        missing_edges = edges1_set.keys() - edges2_set.keys()
        extra_edges = edges2_set.keys() - edges1_set.keys()
        
        if missing_edges:
            for key in missing_edges:
                e = edges1_set[key]
                vars_str = f" [{', '.join(e.get('variables', []))}]" if 'variables' in e else ""
                diffs.append(f"缺失边: {e['source_id']} -> {e['target_id']}{vars_str}")
        
        if extra_edges:
            for key in extra_edges:
                e = edges2_set[key]
                vars_str = f" [{', '.join(e.get('variables', []))}]" if 'variables' in e else ""
                diffs.append(f"多余边: {e['source_id']} -> {e['target_id']}{vars_str}")
        
        return len(diffs) == 0, diffs
    
    def compare_graph(self, graph1: Dict, graph2: Dict) -> Tuple[bool, Dict]:
        """对比两个图"""
        result = {
            'nodes_match': True,
            'edges_match': True,
            'diffs': []
        }
        
        if not graph1 or not graph2:
            if graph1 != graph2:
                result['nodes_match'] = False
                result['edges_match'] = False
                result['diffs'].append("一个图为空，另一个不为空")
            return graph1 == graph2, result
        
        # 对比节点
        nodes_match, node_diffs = self.compare_nodes(graph1['nodes'], graph2['nodes'])
        result['nodes_match'] = nodes_match
        result['diffs'].extend([f"[节点] {d}" for d in node_diffs])
        
        # 对比边
        edges_match, edge_diffs = self.compare_edges(graph1['edges'], graph2['edges'])
        result['edges_match'] = edges_match
        result['diffs'].extend([f"[边] {d}" for d in edge_diffs])
        
        return nodes_match and edges_match, result
    
    def compare_program(self, program_file, graph_filter=None):
        """对比单个程序"""
        program_name = program_file.stem
        print(f"\n{'─'*80}")
        print(f"📝 {program_name}")
        
        # 加载基准
        baseline = self.load_baseline(program_name)
        if not baseline:
            print(f"  ❌ 未找到基准文件，请先运行: python build_baseline.py")
            return {'program': program_name, 'has_baseline': False}
        
        # 读取代码
        code = self.read_code(program_file)
        
        # 对比各类型的图
        graph_types = ['cfg', 'cdg', 'ddg', 'pdg']
        if graph_filter:
            graph_types = [g for g in graph_types if g == graph_filter.lower()]
        
        results = {
            'program': program_name,
            'has_baseline': True,
            'graphs': {}
        }
        
        all_match = True
        
        for graph_type in graph_types:
            # 获取基准图
            baseline_graph_data = baseline['graphs'].get(graph_type, {})
            baseline_graph = baseline_graph_data.get('graph')
            baseline_time = baseline_graph_data.get('time', 0)
            
            if not baseline_graph:
                print(f"  {graph_type.upper()}: ⚠️  基准中无数据")
                results['graphs'][graph_type] = {'has_baseline': False}
                continue
            
            # 构建当前版本的图
            import time
            start = time.time()
            try:
                current_graph_obj = self.build_current_graph(code, graph_type)
                current_time = time.time() - start
                
                if not current_graph_obj:
                    print(f"  {graph_type.upper()}: ❌ 构建失败")
                    results['graphs'][graph_type] = {'match': False, 'error': '构建失败'}
                    all_match = False
                    continue
                
                # 转换为JSON格式
                current_graph = GraphToJSON.graph_to_dict(current_graph_obj, graph_type.upper())
                
                # 对比
                match, compare_result = self.compare_graph(baseline_graph, current_graph)
                
                # 计算性能变化
                speedup = baseline_time / current_time if current_time > 0 else 0
                
                results['graphs'][graph_type] = {
                    'match': match,
                    'baseline_time': baseline_time,
                    'current_time': current_time,
                    'speedup': speedup,
                    'compare_result': compare_result
                }
                
                # 打印结果（紧凑格式）
                status = "✅" if match else "❌"
                nodes = len(current_graph['nodes'])
                edges = len(current_graph['edges'])
                speedup_str = f"{speedup:.2f}x" if speedup >= 1 else f"0.{int(speedup*100):02d}x"
                
                if match:
                    print(f"  {graph_type.upper()}: {status} N={nodes:2d} E={edges:2d} T={current_time:.4f}s (基准:{baseline_time:.4f}s, {speedup_str})")
                else:
                    baseline_n = len(baseline_graph['nodes'])
                    baseline_e = len(baseline_graph['edges'])
                    print(f"  {graph_type.upper()}: {status} 不一致 [基准: N={baseline_n} E={baseline_e}] [当前: N={nodes} E={edges}]")
                    all_match = False
                    
                    if self.verbose and compare_result['diffs']:
                        for diff in compare_result['diffs'][:5]:  # 只显示前5个差异
                            print(f"       • {diff}")
                        if len(compare_result['diffs']) > 5:
                            print(f"       ... 还有 {len(compare_result['diffs']) - 5} 个差异")
                
            except Exception as e:
                print(f"  {graph_type.upper()}: ❌ 对比出错: {e}")
                results['graphs'][graph_type] = {'match': False, 'error': str(e)}
                all_match = False
                if self.verbose:
                    import traceback
                    traceback.print_exc()
        
        results['all_match'] = all_match
        return results
    
    def compare_all(self, program_filter=None, graph_filter=None):
        """对比所有程序"""
        programs = sorted(self.test_programs_dir.glob("*.c"))
        
        if program_filter:
            programs = [p for p in programs if program_filter in p.name]
        
        if not programs:
            print("❌ 未找到测试程序")
            return
        
        filter_info = f" (过滤: {graph_filter.upper()})" if graph_filter else ""
        print(f"{'='*80}")
        print(f"🔬 对比测试: {len(programs)}个程序{filter_info}")
        print(f"{'='*80}")
        
        all_results = []
        summary = {
            'total': len(programs),
            'all_match': 0,
            'has_diff': 0,
            'no_baseline': 0,
            'errors': 0,
            'graph_stats': {}
        }
        
        for program_file in programs:
            result = self.compare_program(program_file, graph_filter)
            all_results.append(result)
            
            if not result['has_baseline']:
                summary['no_baseline'] += 1
            elif result.get('all_match', False):
                summary['all_match'] += 1
            else:
                summary['has_diff'] += 1
        
        # 打印总结（紧凑格式）
        print(f"\n{'='*80}")
        print(f"📊 总结: 共{summary['total']}个程序 | ✅ 一致:{summary['all_match']} | ❌ 差异:{summary['has_diff']} | ⚠️  无基准:{summary['no_baseline']}")
        
        # 统计各图类型的匹配情况
        graph_types = ['cfg', 'cdg', 'ddg', 'pdg']
        graph_stats = []
        for graph_type in graph_types:
            match_count = sum(1 for r in all_results 
                            if r.get('has_baseline') and 
                            r.get('graphs', {}).get(graph_type, {}).get('match', False))
            total_count = sum(1 for r in all_results 
                            if r.get('has_baseline') and 
                            graph_type in r.get('graphs', {}))
            if total_count > 0:
                rate = (match_count / total_count * 100)
                graph_stats.append(f"{graph_type.upper()}:{match_count}/{total_count}({rate:.0f}%)")
        
        if graph_stats:
            print(f"图类型: {' | '.join(graph_stats)}")
        
        print(f"{'='*80}")
        
        if summary['no_baseline'] > 0:
            print(f"💡 提示: 运行 'python build_baseline.py' 生成基准")


def main():
    parser = argparse.ArgumentParser(description='对比测试结果')
    parser.add_argument('--program', type=str, help='只对比指定编号的程序 (如 01, 02)')
    parser.add_argument('--graph', type=str, choices=['cfg', 'cdg', 'ddg', 'pdg'], 
                       help='只对比指定类型的图')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细差异')
    
    args = parser.parse_args()
    
    # 获取目录路径
    script_dir = Path(__file__).parent
    test_programs_dir = script_dir / "test_programs"
    expected_results_dir = script_dir / "expected_results"
    
    # 创建对比器
    comparator = ResultComparator(test_programs_dir, expected_results_dir, verbose=args.verbose)
    
    # 执行对比
    comparator.compare_all(program_filter=args.program, graph_filter=args.graph)


if __name__ == "__main__":
    main()

