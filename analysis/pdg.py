#!/usr/bin/env python3
"""
程序依赖图(PDG)构建器

结合控制流图(CFG)和数据依赖图(DDG)构建程序依赖图
"""

from typing import List, Dict
from .cfg import CFG
from .ddg import DDG
from .utils import Graph, Edge, Node, visualize_pdg


class CDG(CFG):
    """控制依赖图构建器"""
    
    def __init__(self, language: str = "c"):
        """初始化CDG构建器"""
        super().__init__(language)
        self.cdgs: List[Graph] = []
    
    def construct_cdg(self, code: str):
        """构建控制依赖图"""
        if self.check_syntax(code):
            print('Syntax Error')
            return
        
        # 首先构建CFG
        cfgs = self.see_cfg(code, pdf=False)
        
        self.cdgs = []
        for cfg in cfgs:
            cdg = Graph()
            
            # 复制CFG的节点到CDG
            for node in cfg.nodes:
                cdg.add_node(node)
            
            # 构建控制依赖边
            self._build_control_dependencies(cfg, cdg)
            
            self.cdgs.append(cdg)
    
    def _build_control_dependencies(self, cfg: Graph, cdg: Graph):
        """构建控制依赖关系"""
        # 简化的控制依赖分析
        # 对于每个分支节点，其控制的语句都依赖于它
        
        for node in cfg.nodes:
            if node.is_branch:
                # 找到这个分支节点控制的所有节点
                controlled_nodes = self._find_controlled_nodes(cfg, node)
                
                for controlled_node in controlled_nodes:
                    if controlled_node.id != node.id:
                        edge = Edge(controlled_node.id, '', 'CDG')
                        cdg.edges.setdefault(node.id, []).append(edge)
    
    def _find_controlled_nodes(self, cfg: Graph, branch_node: Node) -> List[Node]:
        """找到被分支节点控制的所有节点"""
        controlled = []
        
        # 简化实现：找到分支节点后面的所有节点，直到遇到汇合点
        branch_line = branch_node.line
        
        # 找到分支结构的结束位置（简化：通过缩进或者特定模式）
        for node in cfg.nodes:
            if node.line > branch_line:
                # 简单的启发式：如果节点在分支后面，认为被控制
                # 实际应该通过支配树等算法来精确计算
                if self._is_in_branch_scope(branch_node, node):
                    controlled.append(node)
        
        return controlled
    
    def _is_in_branch_scope(self, branch_node: Node, target_node: Node) -> bool:
        """判断目标节点是否在分支节点的作用域内"""
        # 简化实现：基于行号和节点类型的启发式判断
        if target_node.line <= branch_node.line:
            return False
        
        # 如果目标节点是return语句，且在分支后面，认为被控制
        if target_node.type == 'return_statement':
            return True
        
        # 其他简化的判断逻辑
        return target_node.line < branch_node.line + 10  # 简化的范围判断


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



