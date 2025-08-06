#!/usr/bin/env python3
"""
数据依赖图(DDG)构建器

基于CFG构建数据依赖图
"""

from typing import List, Dict, Set
from .cfg import CFG
from .graph import Graph, Edge
from .ast_nodes import Node
from .visualization import visualize_ddg


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
        cfgs = self.see_cfg(code, pdf=False, dot_format=False)
        
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
        """
        参考DDG.py实现，按照正确的算法构建数据依赖关系
        
        算法参考：https://home.cs.colorado.edu/~kena/classes/5828/s99/lectures/lecture25.pdf 第19页
        """
        edge = {}  # (source_id, target_id) -> {变量集合}
        
        # 转换CFG的defs/uses结构：从 {node_id: set(variables)} 到 {variable: [node_ids]}
        defs = {}  # 变量名 -> 定义该变量的节点ID列表
        uses = {}  # 变量名 -> 使用该变量的节点ID列表
        
        for node_id, vars_set in cfg.defs.items():
            for var in vars_set:
                if var not in defs:
                    defs[var] = []
                defs[var].append(node_id)
        
        for node_id, vars_set in cfg.uses.items():
            for var in vars_set:
                if var not in uses:
                    uses[var] = []
                uses[var].append(node_id)
        
        # 情况1: def X to use Y (def节点到use节点)
        for X in defs:
            if X not in uses:
                continue
            def_nodes = defs[X]
            use_nodes = uses[X]
            
            for d in def_nodes:
                for u in use_nodes:
                    if d == u:  # 跳过同一个节点
                        continue
                    
                    # 检查从d到u的所有路径，是否至少有一条路径没有中间重定义
                    paths = cfg.findAllPath(d, u)
                    for path in paths:
                        is_arrival = True
                        for n in path[1:-1]:  # 检查路径中间节点
                            node = cfg.id_to_nodes[n]
                            if X in node.defs:
                                is_arrival = False
                                break
                        if is_arrival:  # 找到至少一条无中间重定义的路径
                            edge.setdefault((d, u), set())
                            edge[(d, u)].add(X)
                            break  # 找到一条就够了
        
        # 注释掉情况2和情况3，先只测试经典的def→use依赖
        # 情况2: use X to def Y (use节点到def节点) - 反向依赖/输出依赖
        # 情况3: def X to def Y (def节点到def节点) - 写后写依赖
        
        # 构建DDG边 - 注意这里要转换为入边结构
        for (source_id, target_id), vars_set in edge.items():
            ddg_edge = Edge(source_id, '', 'DDG')
            ddg_edge.token = list(vars_set)
            ddg.edges.setdefault(target_id, []).append(ddg_edge)
    
    def see_ddg(self, code: str, filename: str = 'DDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化DDG"""
        self.construct_ddg(code)
        visualize_ddg(self.ddgs, filename, pdf, dot_format, view)
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



