#!/usr/bin/env python3
"""
数据依赖图(DDG)构建器

基于CFG构建数据依赖图
"""

from typing import Optional
from .cfg import CFG
from .graph import Graph, DDGEdge
from .visualization import visualize_ddg

class DDG(CFG):
    """数据依赖图构建器 - 单函数版本"""
    
    def __init__(self, language: str = "c"):
        """初始化DDG构建器"""
        super().__init__(language)
        self.ddg: Optional[Graph] = None  # 单个DDG图
    
    def construct_ddg(self, code: str) -> Optional[Graph]:
        """
        构建数据依赖图 - 单函数版本
        参考算法：https://home.cs.colorado.edu/~kena/classes/5828/s99/lectures/lecture25.pdf
        """
        if self.check_syntax(code):
            print('⚠️  DDG构建警告: 检测到语法错误，但将继续尝试构建DDG')
            # 不直接返回，继续尝试构建DDG
        
        try:
            # 首先构建CFG
            cfg = self.construct_cfg(code)
            if not cfg:
                print('⚠️  DDG构建警告: 未找到任何函数')
                self.ddg = None
                return None
            
            try:
                ddg = Graph()
                
                # 复制CFG的节点到DDG
                for node in cfg.nodes:
                    ddg.add_node(node)
                
                # 构建数据依赖边
                self._build_data_dependencies(cfg, ddg)
                
                self.ddg = ddg
                return ddg
            except Exception as e:
                print(f'⚠️  DDG构建警告: CFG处理失败: {e}')
                self.ddg = None
                return None
        except Exception as e:
            print(f'⚠️  DDG构建警告: 代码解析失败: {e}')
            self.ddg = None
            return None
    
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
                    
                    # 优化v2：使用hasPathAvoidingNodes + BFS
                    # 找出所有重新定义变量X的节点（排除起点d和终点u）
                    avoid_nodes = set()
                    for node_id in def_nodes:
                        if node_id != d and node_id != u:
                            avoid_nodes.add(node_id)
                    
                    # 检查是否存在一条从d到u的路径，不经过其他定义X的节点
                    if cfg.hasPathAvoidingNodes(d, u, avoid_nodes):
                        edge.setdefault((d, u), set())
                        edge[(d, u)].add(X)
                    
                    # 旧实现（性能较差，已弃用）：
                    # 检查从d到u的所有路径，是否至少有一条路径没有中间重定义
                    # paths = cfg.findAllPath(d, u)
                    # for path in paths:
                    #     is_arrival = True
                    #     for n in path[1:-1]:  # 检查路径中间节点
                    #         node = cfg.id_to_nodes[n]
                    #         if X in node.defs:
                    #             is_arrival = False
                    #             break
                    #     if is_arrival:  # 找到至少一条无中间重定义的路径
                    #         edge.setdefault((d, u), set())
                    #         edge[(d, u)].add(X)
                    #         break  # 找到一条就够了
        
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
        
        # 构建DDG边
        for (source_id, target_id), vars_set in edge.items():
            source_node = ddg.id_to_nodes.get(source_id)
            target_node = ddg.id_to_nodes.get(target_id)
            ddg_edge = DDGEdge(label='', variables=list(vars_set), source_node=source_node, target_node=target_node)
            ddg.edges.append(ddg_edge)
    
    def see_ddg(self, code: str, filename: str = 'DDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化DDG - 单函数版本"""
        ddg = self.construct_ddg(code)
        if ddg:
            visualize_ddg([ddg], filename, pdf, dot_format, view)  # 传入单元素列表以兼容可视化函数
        return ddg
    
    def print_ddg_edges(self):
        """打印DDG的边信息，格式：语句A (序号) --> 语句B (序号) [变量]"""
        if not hasattr(self, 'ddg') or not self.ddg:
            print("DDG未构建，请先调用construct_ddg()")
            return
        
        print("=== DDG 边信息 ===")
        if not self.ddg.edges:
            print("该图没有边")
            return
            
        for i, edge in enumerate(self.ddg.edges, 1):
            if edge.source_node and edge.target_node:
                source_text = edge.source_node.text.strip().replace('\n', ' ')
                target_text = edge.target_node.text.strip().replace('\n', ' ')
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                
                # 限制文本长度，避免过长
                if len(source_text) > 50:
                    source_text = source_text[:47] + "..."
                if len(target_text) > 50:
                    target_text = target_text[:47] + "..."
                
                # 显示依赖的变量信息
                variables = []
                if hasattr(edge, 'variables') and edge.variables:
                    variables = edge.variables
                elif hasattr(edge, 'token') and edge.token:
                    variables = edge.token
                
                var_info = f" [变量: {', '.join(variables)}]" if variables else ""
                print(f"{i:3d}. {source_text} ({source_id}) --> {target_text} ({target_id}){var_info}")
            else:
                print(f"{i:3d}. [无效边: 缺少源节点或目标节点]")
        
        print(f"\n总计: {len(self.ddg.edges)} 条边")