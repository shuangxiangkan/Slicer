#!/usr/bin/env python3
"""
程序依赖图(PDG)构建器

结合控制流图(CFG)和数据依赖图(DDG)构建程序依赖图
"""

from typing import List, Dict
from .cfg import CFG
from .cdg import CDG
from .ddg import DDG
from .utils import Graph, Edge, Node, visualize_pdg


class PDG(CFG):
    """程序依赖图构建器"""
    
    def __init__(self, language: str = "c"):
        """初始化PDG构建器"""
        super().__init__(language)
        self.pdgs: List[Graph] = []
    
    def construct_pdg(self, code: str):
        """构建程序依赖图"""
        # 构建CDG和DDG
        cdg = CDG(self.language_name)
        ddg = DDG(self.language_name)
        
        cdg.construct_cdg(code)
        ddg.construct_ddg(code)
        
        self.pdgs = []
        
        # 合并CDG和DDG
        for cdg_graph, ddg_graph in zip(cdg.cdgs, ddg.ddgs):
            pdg = Graph()
            
            # 复制所有节点
            for node in cdg_graph.nodes:
                pdg.add_node(node)
            
            # 复制控制依赖边
            for node_id, edges in cdg_graph.edges.items():
                pdg.edges.setdefault(node_id, [])
                for edge in edges:
                    pdg.edges[node_id].append(edge)
            
            # 添加数据依赖边
            for node_id, edges in ddg_graph.edges.items():
                pdg.edges.setdefault(node_id, [])
                for edge in edges:
                    pdg.edges[node_id].append(edge)
            
            self.pdgs.append(pdg)
    
    def see_pdg(self, code: str, filename: str = 'PDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化PDG"""
        self.construct_pdg(code)
        visualize_pdg(self.pdgs, filename, pdf, dot_format, view)
        return self.pdgs
    
    def get_dependencies(self, code: str) -> List[Dict]:
        """
        获取程序依赖信息
        Returns:
            每个函数的依赖信息列表
        """
        self.construct_pdg(code)
        
        dependencies = []
        for pdg in self.pdgs:
            func_deps = {
                'nodes': len(pdg.nodes),
                'control_dependencies': [],
                'data_dependencies': []
            }
            
            for node_id, edges in pdg.edges.items():
                source_node = pdg.id_to_nodes[node_id]
                for edge in edges:
                    target_node = pdg.id_to_nodes[edge.id]
                    
                    dep_info = {
                        'source': {
                            'id': source_node.id,
                            'line': source_node.line,
                            'text': source_node.text,
                            'type': source_node.type
                        },
                        'target': {
                            'id': target_node.id,
                            'line': target_node.line,
                            'text': target_node.text,
                            'type': target_node.type
                        }
                    }
                    
                    if edge.type == 'DDG':
                        dep_info['variables'] = edge.token
                        func_deps['data_dependencies'].append(dep_info)
                    elif edge.type == 'CDG':
                        func_deps['control_dependencies'].append(dep_info)
            
            dependencies.append(func_deps)
        
        return dependencies
    
    def analyze_function_complexity(self, code: str) -> Dict:
        """分析函数复杂度"""
        self.construct_pdg(code)
        
        complexity_info = {
            'functions': [],
            'total_nodes': 0,
            'total_dependencies': 0
        }
        
        for i, pdg in enumerate(self.pdgs):
            func_info = {
                'function_index': i,
                'nodes': len(pdg.nodes),
                'control_dependencies': 0,
                'data_dependencies': 0,
                'total_dependencies': 0
            }
            
            for edges in pdg.edges.values():
                for edge in edges:
                    if edge.type == 'DDG':
                        func_info['data_dependencies'] += 1
                    elif edge.type == 'CDG':
                        func_info['control_dependencies'] += 1
                    func_info['total_dependencies'] += 1
            
            complexity_info['functions'].append(func_info)
            complexity_info['total_nodes'] += func_info['nodes']
            complexity_info['total_dependencies'] += func_info['total_dependencies']
        
        return complexity_info



