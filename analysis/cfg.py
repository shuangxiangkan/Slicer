#!/usr/bin/env python3
"""
控制流图(CFG)构建器

基于tree-sitter构建函数级控制流图
"""

import html
from graphviz import Digraph
from typing import List, Tuple, Optional
from .utils import BaseAnalyzer, Node, Graph, Edge, text





class CFG(BaseAnalyzer):
    """控制流图构建器"""

    def __init__(self, language: str = "c"):
        """初始化CFG构建器"""
        super().__init__(language)
        self.cfgs: List[Graph] = []

    def get_break_continue_nodes(self, node):
        """找到节点循环中的所有break和continue节点"""
        break_nodes, continue_nodes = [], []
        for child in node.children:
            if child.type == 'break_statement':
                break_nodes.append(child)
            elif child.type == 'continue_statement':
                continue_nodes.append(child)
            elif child.type not in ['for_statement', 'while_statement']:
                b_nodes, c_nodes = self.get_break_continue_nodes(child)
                break_nodes.extend(b_nodes)
                continue_nodes.extend(c_nodes)
        return break_nodes, continue_nodes

    def get_edge(self, in_nodes):
        """输入入节点，返回入边的列表，边为(parent_id, label)"""
        edge = []
        for in_node in in_nodes:
            parent, label = in_node
            if parent:
                parent_id = parent.id
                edge.append((parent_id, label))
        return edge

    def create_cfg(self, node, in_nodes=[()]):
        """
        递归创建CFG
        Args:
            node: 当前tree-sitter节点
            in_nodes: 入节点列表，格式为[(node_info, edge_label), ...]
        Returns:
            (CFG_edges, out_nodes): CFG边列表和出节点列表
        """
        if node.child_count == 0 or in_nodes == []:
            return [], in_nodes
        
        if node.type == 'function_definition':
            # 如果节点是函数，则创建函数节点，并且递归遍历函数的compound_statement
            body = node.child_by_field_name('body')
            node_info = Node(node)
            CFG, _ = self.create_cfg(body, [(node_info, '')])
            return CFG + [(node_info, [])], []

        elif node.type == 'compound_statement':
            # 如果是复合语句，则递归遍历复合语句的每一条statement
            CFG = []
            for child in node.children:
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes

        elif node.type not in ['if_statement', 'while_statement', 'for_statement', 'switch_statement', 'case_statement', 'translation_unit', 'do_statement']:
            # 如果是普通的语句
            edge = self.get_edge(in_nodes)
            node_info = Node(node)
            in_nodes = [(node_info, '')]
            if node.type in ['return_statement', 'break_statement', 'continue_statement']:
                # return，break，continue语句没有出节点
                return [(node_info, edge)], []
            else:
                return [(node_info, edge)], in_nodes

        elif node.type == 'if_statement':
            return self._handle_if_statement(node, in_nodes)

        elif node.type in ['while_statement', 'for_statement']:
            return self._handle_loop_statement(node, in_nodes)

        elif node.type == 'switch_statement':
            return self._handle_switch_statement(node, in_nodes)

        elif node.type == 'case_statement':
            return self._handle_case_statement(node, in_nodes)

        else:
            CFGs = []  # 存放每一个函数的CFG图
            for child in node.children:
                if child.type == 'function_definition':  # 获得每一个函数的CFG图
                    CFG, out_nodes = self.create_cfg(child, in_nodes)
                    CFGs.append(CFG)
            return CFGs, in_nodes
    
    def _handle_if_statement(self, node, in_nodes):
        """处理if语句"""
        CFG = []
        edge = self.get_edge(in_nodes)
        node_info = Node(node)
        CFG.append((node_info, edge))

        # 处理then分支
        consequence = node.child_by_field_name('consequence')
        cfg, then_out = self.create_cfg(consequence, [(node_info, 'Y')])
        CFG.extend(cfg)

        # 处理else分支
        alternative = node.child_by_field_name('alternative')
        if alternative:
            cfg, else_out = self.create_cfg(alternative, [(node_info, 'N')])
            CFG.extend(cfg)
            out_nodes = then_out + else_out
        else:
            out_nodes = then_out + [(node_info, 'N')]

        return CFG, out_nodes
    
    def _handle_loop_statement(self, node, in_nodes):
        """处理循环语句"""
        CFG = []
        edge = self.get_edge(in_nodes)
        node_info = Node(node)
        CFG.append((node_info, edge))

        # 处理循环体
        body = node.child_by_field_name('body')
        cfg, body_out = self.create_cfg(body, [(node_info, 'Y')])
        CFG.extend(cfg)

        # 循环体的出口回到条件 - 为循环条件节点添加来自循环体出口的边
        loop_back_edges = []
        for out_node, _ in body_out:
            if out_node:
                loop_back_edges.append((out_node.id, ''))

        # 更新循环条件节点的入边，添加回边
        if loop_back_edges:
            for i, (cfg_node, cfg_edges) in enumerate(CFG):
                if cfg_node.id == node_info.id:
                    CFG[i] = (cfg_node, cfg_edges + loop_back_edges)
                    break

        # 处理break和continue语句
        break_nodes, continue_nodes = self.get_break_continue_nodes(node)
        out_nodes = [(node_info, 'N')]  # 循环条件为false时跳出

        for break_node in break_nodes:
            out_nodes.append((Node(break_node), ''))

        for continue_node in continue_nodes:
            # 为continue节点添加到循环条件的边
            continue_node_info = Node(continue_node)
            for i, (cfg_node, cfg_edges) in enumerate(CFG):
                if cfg_node.id == continue_node_info.id:
                    CFG[i] = (cfg_node, cfg_edges + [(node_info.id, '')])
                    break

        return CFG, out_nodes
    
    def _handle_switch_statement(self, node, in_nodes):
        """处理switch语句"""
        CFG = []
        edge = self.get_edge(in_nodes)
        node_info = Node(node)
        CFG.append((node_info, edge))

        # 处理switch体
        body = node.child_by_field_name('body')
        if body:
            cfg, body_out = self.create_cfg(body, [(node_info, '')])
            CFG.extend(cfg)

            # 处理break语句
            break_nodes, _ = self.get_break_continue_nodes(node)
            for break_node in break_nodes:
                body_out.append((Node(break_node), ''))

            return CFG, body_out

        return CFG, [(node_info, '')]

    def _handle_case_statement(self, node, in_nodes):
        """处理case语句"""
        CFG = []
        edge = self.get_edge(in_nodes)
        node_info = Node(node)
        CFG.append((node_info, edge))

        if node.children and node.children[0].type == 'case':
            # case语句
            in_nodes = [(node_info, 'Y')]
            for child in node.children[3:]:  # 跳过 'case', 'value', ':'
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes + [(node_info, 'N')]
        else:
            # default语句
            in_nodes = [(node_info, '')]
            for child in node.children[2:]:  # 跳过 'default', ':'
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes
    
    def construct_cfg(self, code: str):
        """构建CFG"""
        if self.check_syntax(code):
            print('Syntax Error')
            return

        root_node = self.parse_code(code)
        functions = self.find_functions(root_node)

        self.cfgs = []
        for func_node in functions:
            cfg_edges, _ = self.create_cfg(func_node)

            # 构建图对象
            cfg = Graph()
            for node_info, edges in cfg_edges:
                cfg.add_node(node_info)
                # 转换边格式 - edges是入边列表，存储为入边
                edge_list = []
                for edge_info in edges:
                    if isinstance(edge_info, tuple) and len(edge_info) == 2:
                        source_id, label = edge_info
                        edge = Edge(source_id, label)
                        edge_list.append(edge)
                cfg.edges[node_info.id] = edge_list

            cfg.get_def_use_info()
            self.cfgs.append(cfg)
    
    def see_cfg(self, code: str, filename: str = 'CFG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化CFG"""
        self.construct_cfg(code)

        dot = Digraph(comment=filename, strict=True)
        dot.attr(rankdir='TB')
        dot.attr('node', fontname='Arial')
        dot.attr('edge', fontname='Arial')

        for cfg in self.cfgs:
            for node in cfg.nodes:
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

            for node_id, edges in cfg.edges.items():
                for edge in edges:
                    source_id = edge.id  # 这里edge.id实际上是source
                    target_id = node_id  # 当前节点是target
                    label = edge.label if edge.label else ''
                    dot.edge(str(source_id), str(target_id), label=label)

        # 保存.dot文件
        if dot_format:
            with open(f"{filename}.dot", 'w') as f:
                f.write(dot.source)

        # 生成PDF文件
        if pdf:
            dot.render(filename, view=view, cleanup=True)

        return self.cfgs



