#!/usr/bin/env python3
"""
数据依赖图(DDG)构建器

基于CFG构建数据依赖图
"""

import html
from graphviz import Digraph
from typing import List, Dict, Set
from .cfg import CFG
from .utils import Graph, Edge, Node


class DDG(CFG):
    """数据依赖图构建器"""
    
    def __init__(self, language: str = "c"):
        """初始化DDG构建器"""
        super().__init__(language)
        self.ddgs: List[Graph] = []
    
    def construct_ddg(self, code: str):
        """
        构建数据依赖图
        参考算法：https://home.cs.colorado.edu/~kena/classes/5828/s99/lectures/lecture25.pdf
        """
        if self.check_syntax(code):
            print('Syntax Error')
            return
        
        # 首先构建CFG
        cfgs = self.see_cfg(code, pdf=False)
        
        self.ddgs = []
        for cfg in cfgs:
            ddg = Graph()
            
            # 复制CFG的节点到DDG
            for node in cfg.nodes:
                ddg.add_node(node)
            
            # 构建数据依赖边
            self._build_data_dependencies(cfg, ddg)
            
            self.ddgs.append(ddg)
    
    def _build_data_dependencies(self, cfg: Graph, ddg: Graph):
        """构建数据依赖关系"""
        defs = cfg.defs
        uses = cfg.uses
        
        # 数据依赖的三种情况：
        # 1. def X to use Y: X定义变量v，Y使用变量v
        # 2. use X to def Y: X使用变量v，Y定义变量v  
        # 3. def X to def Y: X定义变量v，Y定义变量v
        
        # 情况1: def X to use Y
        for x_id in defs:
            if x_id not in uses:
                continue
            
            x_defs = defs[x_id]
            for y_id in uses:
                if x_id == y_id:
                    continue
                
                y_uses = uses[y_id]
                
                # 检查是否有共同变量
                common_vars = x_defs.intersection(y_uses)
                if common_vars and self._has_path_without_redefinition(cfg, x_id, y_id, common_vars):
                    # 添加数据依赖边
                    edge = Edge(y_id, '', 'DDG')
                    edge.token = list(common_vars)
                    ddg.edges.setdefault(x_id, []).append(edge)
        
        # 情况2: use X to def Y
        for x_id in uses:
            x_uses = uses[x_id]
            for y_id in defs:
                if x_id == y_id:
                    continue
                
                y_defs = defs[y_id]
                
                # 检查是否有共同变量
                common_vars = x_uses.intersection(y_defs)
                if common_vars and self._has_path_without_redefinition(cfg, x_id, y_id, common_vars):
                    # 添加数据依赖边
                    edge = Edge(y_id, '', 'DDG')
                    edge.token = list(common_vars)
                    ddg.edges.setdefault(x_id, []).append(edge)
        
        # 情况3: def X to def Y
        for x_id in defs:
            x_defs = defs[x_id]
            for y_id in defs:
                if x_id == y_id:
                    continue
                
                y_defs = defs[y_id]
                
                # 检查是否有共同变量
                common_vars = x_defs.intersection(y_defs)
                if common_vars and self._has_path_without_redefinition(cfg, x_id, y_id, common_vars):
                    # 添加数据依赖边
                    edge = Edge(y_id, '', 'DDG')
                    edge.token = list(common_vars)
                    ddg.edges.setdefault(x_id, []).append(edge)
    
    def _has_path_without_redefinition(self, cfg: Graph, start_id: int, end_id: int, variables: Set[str]) -> bool:
        """
        检查从start_id到end_id是否存在路径，且路径上没有重新定义variables中的变量
        简化实现：假设如果两个节点在同一个函数中，就认为存在路径
        """
        # 简化的路径检查：检查是否在同一个CFG中
        start_node = cfg.id_to_nodes.get(start_id)
        end_node = cfg.id_to_nodes.get(end_id)
        
        if not start_node or not end_node:
            return False
        
        # 简化：如果start节点的行号小于end节点，认为存在路径
        if start_node.line < end_node.line:
            # 检查中间是否有重新定义
            return self._check_no_redefinition_between(cfg, start_id, end_id, variables)
        
        return False
    
    def _check_no_redefinition_between(self, cfg: Graph, start_id: int, end_id: int, variables: Set[str]) -> bool:
        """检查两个节点之间是否没有重新定义指定变量"""
        start_line = cfg.id_to_nodes[start_id].line
        end_line = cfg.id_to_nodes[end_id].line
        
        # 检查中间的节点是否重新定义了变量
        for node in cfg.nodes:
            if start_line < node.line < end_line:
                # 检查这个节点是否定义了我们关心的变量
                node_defs = cfg.defs.get(node.id, set())
                if variables.intersection(node_defs):
                    return False
        
        return True
    
    def see_ddg(self, code: str, filename: str = 'DDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化DDG"""
        self.construct_ddg(code)

        dot = Digraph(comment=filename, strict=True)
        dot.attr(rankdir='TB')
        dot.attr('node', fontname='Arial')
        dot.attr('edge', fontname='Arial')

        for ddg in self.ddgs:
            # 添加节点
            for node in ddg.nodes:
                # 对于函数定义，显示完整签名
                if node.type == 'function_definition':
                    label = f"<{html.escape(node.text)}<SUB>{node.line}</SUB>>"
                    dot.node(str(node.id), label=label, shape='ellipse', style='filled', fillcolor='lightblue')
                else:
                    # 使用不同字体显示节点类型，源代码用正常字体
                    type_label = f"<I>{node.type}</I>"  # 斜体显示节点类型
                    code_label = html.escape(node.text)
                    label = f"<{type_label}<BR/>{code_label}<SUB>{node.line}</SUB>>"
                    if node.is_branch:
                        dot.node(str(node.id), shape='diamond', label=label)
                    else:
                        dot.node(str(node.id), shape='rectangle', label=label)

            # 添加数据依赖边
            for node_id, edges in ddg.edges.items():
                for edge in edges:
                    if edge.type == 'DDG':
                        target_id = edge.id
                        var_label = ', '.join(edge.token) if edge.token else ''
                        dot.edge(str(node_id), str(target_id),
                                label=var_label, style='dotted', color='red')

        # 保存.dot文件
        if dot_format:
            with open(f"{filename}.dot", 'w') as f:
                f.write(dot.source)

        # 生成PDF文件
        if pdf:
            dot.render(filename, view=view, cleanup=True)

        return self.ddgs
    
    def get_data_dependencies(self, code: str) -> List[Dict]:
        """
        获取数据依赖关系信息
        Returns:
            每个函数的数据依赖信息列表
        """
        self.construct_ddg(code)
        
        dependencies = []
        for ddg in self.ddgs:
            func_deps = {
                'nodes': len(ddg.nodes),
                'dependencies': []
            }
            
            for node_id, edges in ddg.edges.items():
                source_node = ddg.id_to_nodes[node_id]
                for edge in edges:
                    if edge.type == 'DDG':
                        target_node = ddg.id_to_nodes[edge.id]
                        func_deps['dependencies'].append({
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
                            },
                            'variables': edge.token
                        })
            
            dependencies.append(func_deps)
        
        return dependencies



