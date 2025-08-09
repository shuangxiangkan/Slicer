#!/usr/bin/env python3
"""
程序依赖图(PDG)构建器

结合控制流图(CFG)和数据依赖图(DDG)构建程序依赖图
"""

from typing import List, Dict, Optional
from .cfg import CFG
from .cdg import CDG
from .ddg import DDG
from .graph import Graph, Edge
from .node import Node
from .visualization import visualize_pdg


class PDG(CFG):
    """程序依赖图构建器 - 单函数版本"""
    
    def __init__(self, language: str = "c"):
        """初始化PDG构建器"""
        super().__init__(language)
        self.pdg: Optional[Graph] = None  # 单个PDG图
    
    def construct_pdg(self, code: str) -> Optional[Graph]:
        """构建程序依赖图 - 单函数版本"""
        try:
            # 构建CDG和DDG
            cdg_builder = CDG(self.language_name)
            ddg_builder = DDG(self.language_name)
            
            cdg_graph = cdg_builder.construct_cdg(code)
            ddg_graph = ddg_builder.construct_ddg(code)
            
            if not cdg_graph or not ddg_graph:
                print('⚠️  PDG构建警告: CDG或DDG构建失败')
                self.pdg = None
                return None
            
            try:
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
                
                self.pdg = pdg
                return pdg
            except Exception as e:
                print(f'⚠️  PDG构建警告: 图合并失败: {e}')
                self.pdg = None
                return None
        except Exception as e:
            print(f'⚠️  PDG构建警告: CDG/DDG构建失败: {e}')
            self.pdg = None
            return None
    
    def see_pdg(self, code: str, filename: str = 'PDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化PDG - 单函数版本"""
        pdg = self.construct_pdg(code)
        if pdg:
            visualize_pdg([pdg], filename, pdf, dot_format, view)  # 传入单元素列表以兼容可视化函数
        return pdg
    
    def get_dependencies(self, code: str) -> Optional[Dict]:
        """
        获取程序依赖信息 - 单函数版本
        Returns:
            单个函数的依赖信息
        """
        pdg = self.construct_pdg(code)
        if not pdg:
            return None
        
        func_deps = {
            'nodes': len(pdg.nodes),
            'control_dependencies': [],
            'data_dependencies': []
        }
        
        for node_id, edges in pdg.edges.items():
            source_node = pdg.id_to_nodes[node_id]
            for edge in edges:
                if edge.source_node:
                    target_node = pdg.id_to_nodes[edge.source_node.id]
                    
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
        
        return func_deps
    
    def analyze_function_complexity(self, code: str) -> Optional[Dict]:
        """分析函数复杂度 - 单函数版本"""
        pdg = self.construct_pdg(code)
        if not pdg:
            return None
        
        func_info = {
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
        
        return func_info



