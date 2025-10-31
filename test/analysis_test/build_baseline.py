#!/usr/bin/env python3
"""
构建测试基准 - 将所有测试程序的CFG/CDG/DDG/PDG转换为JSON格式

用法:
    python build_baseline.py                    # 构建所有测试程序的基准
    python build_baseline.py --program 01      # 只构建指定编号的程序
    python build_baseline.py --clean           # 清理已有的基准文件
"""

import sys
import os
import json
import glob
import argparse
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from analysis import CFG, CDG, DDG, PDG


class GraphToJSON:
    """将图结构转换为JSON格式"""
    
    @staticmethod
    def node_to_dict(node):
        """将节点转换为字典"""
        return {
            'id': node.id,
            'type': node.type,
            'text': node.text.strip(),
            'line': node.line,
            'defs': list(node.defs) if node.defs else [],
            'uses': list(node.uses) if node.uses else []
        }
    
    @staticmethod
    def edge_to_dict(edge):
        """将边转换为字典"""
        edge_dict = {
            'source_id': edge.source_node.id if edge.source_node else None,
            'target_id': edge.target_node.id if edge.target_node else None,
            'label': edge.label if hasattr(edge, 'label') else '',
            'type': edge.type.value if hasattr(edge, 'type') else 'unknown'
        }
        
        # DDG边包含变量信息
        if hasattr(edge, 'variables'):
            edge_dict['variables'] = edge.variables
        
        return edge_dict
    
    @staticmethod
    def graph_to_dict(graph, graph_type):
        """将图转换为字典"""
        if not graph:
            return None
        
        return {
            'graph_type': graph_type,
            'nodes': [GraphToJSON.node_to_dict(node) for node in graph.nodes],
            'edges': [GraphToJSON.edge_to_dict(edge) for edge in graph.edges],
            'node_count': len(graph.nodes),
            'edge_count': len(graph.edges)
        }


class BaselineBuilder:
    """基准构建器"""
    
    def __init__(self, test_programs_dir, expected_results_dir):
        self.test_programs_dir = Path(test_programs_dir)
        self.expected_results_dir = Path(expected_results_dir)
        self.expected_results_dir.mkdir(exist_ok=True)
        
    def get_all_test_programs(self):
        """获取所有测试程序"""
        c_files = sorted(self.test_programs_dir.glob("*.c"))
        return c_files
    
    def read_code(self, file_path):
        """读取C代码"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def build_cfg(self, code):
        """构建CFG"""
        cfg_builder = CFG("c")
        cfg = cfg_builder.construct_cfg(code)
        return cfg
    
    def build_cdg(self, code):
        """构建CDG"""
        cdg_builder = CDG("c")
        cdg = cdg_builder.construct_cdg(code)
        return cdg
    
    def build_ddg(self, code):
        """构建DDG"""
        ddg_builder = DDG("c")
        ddg = ddg_builder.construct_ddg(code)
        return ddg
    
    def build_pdg(self, code):
        """构建PDG"""
        pdg_builder = PDG("c")
        pdg = pdg_builder.construct_pdg(code)
        return pdg
    
    def build_all_graphs(self, code):
        """构建所有图"""
        results = {}
        
        print("    构建 CFG...", end='')
        start = time.time()
        try:
            cfg = self.build_cfg(code)
            results['cfg'] = {
                'graph': GraphToJSON.graph_to_dict(cfg, 'CFG'),
                'time': time.time() - start,
                'success': cfg is not None
            }
            print(f" ✓ ({results['cfg']['time']:.3f}s)")
        except Exception as e:
            results['cfg'] = {'graph': None, 'time': time.time() - start, 'success': False, 'error': str(e)}
            print(f" ✗ {e}")
        
        print("    构建 CDG...", end='')
        start = time.time()
        try:
            cdg = self.build_cdg(code)
            results['cdg'] = {
                'graph': GraphToJSON.graph_to_dict(cdg, 'CDG'),
                'time': time.time() - start,
                'success': cdg is not None
            }
            print(f" ✓ ({results['cdg']['time']:.3f}s)")
        except Exception as e:
            results['cdg'] = {'graph': None, 'time': time.time() - start, 'success': False, 'error': str(e)}
            print(f" ✗ {e}")
        
        print("    构建 DDG...", end='')
        start = time.time()
        try:
            ddg = self.build_ddg(code)
            results['ddg'] = {
                'graph': GraphToJSON.graph_to_dict(ddg, 'DDG'),
                'time': time.time() - start,
                'success': ddg is not None
            }
            print(f" ✓ ({results['ddg']['time']:.3f}s)")
        except Exception as e:
            results['ddg'] = {'graph': None, 'time': time.time() - start, 'success': False, 'error': str(e)}
            print(f" ✗ {e}")
        
        print("    构建 PDG...", end='')
        start = time.time()
        try:
            pdg = self.build_pdg(code)
            results['pdg'] = {
                'graph': GraphToJSON.graph_to_dict(pdg, 'PDG'),
                'time': time.time() - start,
                'success': pdg is not None
            }
            print(f" ✓ ({results['pdg']['time']:.3f}s)")
        except Exception as e:
            results['pdg'] = {'graph': None, 'time': time.time() - start, 'success': False, 'error': str(e)}
            print(f" ✗ {e}")
        
        return results
    
    def build_baseline_for_program(self, program_file):
        """为单个程序构建基准"""
        program_name = program_file.stem
        print(f"\n📝 处理: {program_name}")
        
        # 读取代码
        code = self.read_code(program_file)
        print(f"    代码行数: {code.count(chr(10)) + 1}")
        
        # 构建所有图
        results = self.build_all_graphs(code)
        
        # 添加元数据
        baseline = {
            'program_name': program_name,
            'program_file': program_file.name,
            'code_lines': code.count('\n') + 1,
            'code': code,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'graphs': results
        }
        
        # 保存到JSON文件
        output_file = self.expected_results_dir / f"{program_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
        
        print(f"    ✅ 基准已保存: {output_file.name}")
        
        return baseline
    
    def build_all_baselines(self, program_filter=None):
        """构建所有基准"""
        programs = self.get_all_test_programs()
        
        if program_filter:
            programs = [p for p in programs if program_filter in p.name]
        
        if not programs:
            print("❌ 未找到测试程序")
            return
        
        print(f"{'='*80}")
        print(f"🚀 准备构建基准")
        print(f"{'='*80}")
        print(f"测试程序目录: {self.test_programs_dir}")
        print(f"结果输出目录: {self.expected_results_dir}")
        print(f"找到 {len(programs)} 个测试程序")
        print(f"{'='*80}")
        
        # 检查是否已有基准文件
        existing_baselines = list(self.expected_results_dir.glob("*.json"))
        if existing_baselines:
            print(f"⚠️  警告: 发现 {len(existing_baselines)} 个已有基准文件")
            print(f"   继续操作将覆盖现有基准！")
        
        # 要求确认
        print(f"\n❓ 确认要构建基准吗？这将作为后续对比的标准。")
        print(f"   请输入 'yes' 或 'y' 继续: ", end='')
        confirm = input().strip().lower()
        
        if confirm not in ['yes', 'y']:
            print("❌ 已取消构建")
            return
        
        print(f"\n{'='*80}")
        print(f"✅ 开始构建基准")
        print(f"{'='*80}")
        
        total_start = time.time()
        summary = {
            'total': len(programs),
            'success': 0,
            'failed': 0,
            'graph_stats': {'cfg': 0, 'cdg': 0, 'ddg': 0, 'pdg': 0}
        }
        
        for program_file in programs:
            try:
                baseline = self.build_baseline_for_program(program_file)
                summary['success'] += 1
                
                # 统计各图的成功情况
                for graph_type in ['cfg', 'cdg', 'ddg', 'pdg']:
                    if baseline['graphs'][graph_type]['success']:
                        summary['graph_stats'][graph_type] += 1
                
            except Exception as e:
                print(f"    ❌ 构建失败: {e}")
                summary['failed'] += 1
                import traceback
                traceback.print_exc()
        
        total_time = time.time() - total_start
        
        # 打印总结
        print(f"\n{'='*80}")
        print(f"📊 构建总结")
        print(f"{'='*80}")
        print(f"总程序数: {summary['total']}")
        print(f"成功: {summary['success']}")
        print(f"失败: {summary['failed']}")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"\n各图类型成功率:")
        for graph_type, count in summary['graph_stats'].items():
            rate = (count / summary['total'] * 100) if summary['total'] > 0 else 0
            print(f"  {graph_type.upper()}: {count}/{summary['total']} ({rate:.1f}%)")
        print(f"{'='*80}")
    
    def clean_baselines(self):
        """清理已有的基准文件"""
        json_files = list(self.expected_results_dir.glob("*.json"))
        if not json_files:
            print("没有基准文件需要清理")
            return
        
        print(f"找到 {len(json_files)} 个基准文件，确认删除？(y/N): ", end='')
        confirm = input().strip().lower()
        
        if confirm == 'y':
            for f in json_files:
                f.unlink()
                print(f"  已删除: {f.name}")
            print(f"✅ 已清理 {len(json_files)} 个基准文件")
        else:
            print("已取消")


def main():
    parser = argparse.ArgumentParser(description='构建测试基准')
    parser.add_argument('--program', type=str, help='只构建指定编号的程序 (如 01, 02)')
    parser.add_argument('--clean', action='store_true', help='清理已有的基准文件')
    
    args = parser.parse_args()
    
    # 获取目录路径
    script_dir = Path(__file__).parent
    test_programs_dir = script_dir / "test_programs"
    expected_results_dir = script_dir / "expected_results"
    
    # 创建构建器
    builder = BaselineBuilder(test_programs_dir, expected_results_dir)
    
    if args.clean:
        builder.clean_baselines()
    else:
        builder.build_all_baselines(program_filter=args.program)


if __name__ == "__main__":
    main()

