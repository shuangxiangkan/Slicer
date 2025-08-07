#!/usr/bin/env python3
"""
数据依赖图(DDG)构建器

基于CFG构建数据依赖图
"""

from typing import List, Dict, Set
from .cfg import CFG
from .graph import Graph, Edge
from .node import Node
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
            print('⚠️  DDG构建警告: 检测到语法错误，但将继续尝试构建DDG')
            # 不直接返回，继续尝试构建DDG
        
        try:
            # 首先构建CFG
            cfgs = self.see_cfg(code, pdf=False, dot_format=False)
            
            self.ddgs = []
            for cfg in cfgs:
                try:
                    ddg = Graph()
                    
                    # 复制CFG的节点到DDG
                    for node in cfg.nodes:
                        ddg.add_node(node)
                    
                    # 构建数据依赖边
                    self._build_data_dependencies(cfg, ddg)
                    
                    self.ddgs.append(ddg)
                except Exception as e:
                    print(f'⚠️  DDG构建警告: CFG处理失败: {e}')
                    continue
        except Exception as e:
            print(f'⚠️  DDG构建警告: 代码解析失败: {e}')
            self.ddgs = []
    
    def _build_data_dependencies(self, cfg: Graph, ddg: Graph):
        """
        算法参考：https://home.cs.colorado.edu/~kena/classes/5828/s99/lectures/lecture25.pdf 第19页
        
        数据依赖的三种情况：
        1. X contains a definition of v and Y a use of v (def → use), True Dependence / Read After Write, RAW
        2. X contains a use of v and Y a definition of v (use → def), Anti Dependence / Write After Read, WAR
        3. X contains a definition of v and Y a definition of v (def → def), Output Dependence / Write After Write,WAW
        
        针对程序切片, 只考虑True Dependence, 即RAW依赖, 其他依赖关系主要在并行优化时使用。
        当前实现：只构建真实依赖（def → use），反依赖和输出依赖已注释。
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
        
        # 情况2: use X to def Y (use节点到def节点) - 反向依赖/输出依赖
        # 注释：程序切片通常只考虑真实依赖，反依赖主要用于并行化分析
        # for X in uses:
        #     if X not in defs:
        #         continue
        #     use_nodes = uses[X]
        #     def_nodes = defs[X]
        #     
        #     for u in use_nodes:
        #         for d in def_nodes:
        #             if u == d:  # 跳过同一个节点
        #                 continue
        #             
        #             # 检查从u到d的所有路径，是否至少有一条路径没有中间重定义
        #             paths = cfg.findAllPath(u, d)
        #             for path in paths:
        #                 is_arrival = True
        #                 for n in path[1:-1]:  # 检查路径中间节点
        #                     node = cfg.id_to_nodes[n]
        #                     if X in node.defs:
        #                         is_arrival = False
        #                         break
        #                 if is_arrival:  # 找到至少一条无中间重定义的路径
        #                     edge.setdefault((u, d), set())
        #                     edge[(u, d)].add(X)
        #                     break  # 找到一条就够了
        
        # 情况3: def X to def Y (def节点到def节点) - 写后写依赖
        # 注释：程序切片通常只考虑真实依赖，输出依赖主要用于并行化分析
        # for X in defs:
        #     def_nodes = defs[X]
        #     
        #     for d1 in def_nodes:
        #         for d2 in def_nodes:
        #             if d1 == d2:  # 跳过同一个节点
        #                 continue
        #             
        #             # 检查从d1到d2的所有路径，是否至少有一条路径没有中间重定义
        #             paths = cfg.findAllPath(d1, d2)
        #             for path in paths:
        #                 is_arrival = True
        #                 for n in path[1:-1]:  # 检查路径中间节点
        #                     node = cfg.id_to_nodes[n]
        #                     if X in node.defs:
        #                         is_arrival = False
        #                         break
        #                 if is_arrival:  # 找到至少一条无中间重定义的路径
        #                     edge.setdefault((d1, d2), set())
        #                     edge[(d1, d2)].add(X)
        #                     break  # 找到一条就够了
        
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



