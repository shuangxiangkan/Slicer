#!/usr/bin/env python3
"""
工具类和数据结构

提供程序分析所需的基础数据结构和工具函数
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser
from typing import List, Dict, Set, Optional, Any
import re
from graphviz import Digraph
import html


def text(node) -> str:
    """获取节点的文本内容"""
    return node.text.decode('utf-8')


class Node:
    """程序分析节点"""
    
    def __init__(self, tree_sitter_node):
        """
        从tree-sitter节点创建分析节点
        Args:
            tree_sitter_node: tree-sitter解析的节点
        """
        self.line = tree_sitter_node.start_point[0] + 1
        self.type = tree_sitter_node.type
        self.id = hash((tree_sitter_node.start_point, tree_sitter_node.end_point)) % 1000000
        self.is_branch = False
        
        # 根据节点类型设置文本和分支标记
        if tree_sitter_node.type == 'function_definition':
            # 获取完整的函数签名（返回类型 + 函数名 + 参数）
            declarator = tree_sitter_node.child_by_field_name('declarator')
            type_node = tree_sitter_node.child_by_field_name('type')

            if declarator and type_node:
                # 构建完整签名：返回类型 + 函数声明
                return_type = text(type_node)
                func_declarator = text(declarator)
                self.text = f"{return_type} {func_declarator}"
            elif declarator:
                self.text = text(declarator)
            else:
                self.text = 'function'
        elif tree_sitter_node.type in ['if_statement', 'while_statement', 'for_statement', 'switch_statement']:
            if tree_sitter_node.type == 'if_statement':
                body = tree_sitter_node.child_by_field_name('consequence')
            else:
                body = tree_sitter_node.child_by_field_name('body')
            
            node_text = ''
            for child in tree_sitter_node.children:
                if child == body:
                    break
                node_text += text(child)
            self.text = node_text
            
            if tree_sitter_node.type != 'switch_statement':
                self.is_branch = True
        elif tree_sitter_node.type == 'do_statement':
            condition = tree_sitter_node.child_by_field_name("condition")
            if condition:
                self.text = f'while{text(condition)}'
            else:
                self.text = 'do-while'
            self.is_branch = True
        elif tree_sitter_node.type == 'case_statement':
            node_text = ''
            for child in tree_sitter_node.children:
                if child.type == ':':
                    break
                node_text += ' ' + text(child)
            self.text = node_text
            self.is_branch = True
        else:
            self.text = text(tree_sitter_node)
        
        # 获取定义和使用信息
        self.defs, self.uses = self._get_def_use_info(tree_sitter_node)
    
    def _get_def_use_info(self, node):
        """获取节点的定义和使用信息"""
        defs = set()
        uses = set()
        
        # 获取所有标识符
        identifiers = self._get_all_identifiers(node)
        
        # 分析定义和使用
        for identifier in identifiers:
            if self._is_definition(identifier, node):
                defs.add(text(identifier))
            else:
                uses.add(text(identifier))
        
        return defs, uses
    
    def _get_all_identifiers(self, node):
        """获取节点中的所有标识符"""
        identifiers = []
        
        def collect_identifiers(n):
            if n is None:
                return
            if n.type == 'identifier' and n.parent and n.parent.type not in ['call_expression']:
                identifiers.append(n)
            for child in n.children:
                collect_identifiers(child)
        
        collect_identifiers(node)
        return identifiers
    
    def _is_definition(self, identifier_node, context_node):
        """判断标识符是否为定义"""
        parent = identifier_node.parent
        if not parent:
            return False
        
        # 变量声明
        if parent.type in ['declaration', 'init_declarator']:
            return True
        
        # 赋值表达式的左侧
        if parent.type == 'assignment_expression':
            left = parent.child_by_field_name('left')
            if left and self._contains_node(left, identifier_node):
                return True
        
        # 更新表达式 (++, --)
        if parent.type == 'update_expression':
            return True
        
        return False
    
    def _contains_node(self, parent, target):
        """检查父节点是否包含目标节点"""
        if parent == target:
            return True
        for child in parent.children:
            if self._contains_node(child, target):
                return True
        return False


class Edge:
    """图的边"""
    
    def __init__(self, target_id: int, label: str = '', edge_type: str = 'CFG'):
        """
        创建边
        Args:
            target_id: 目标节点ID
            label: 边的标签
            edge_type: 边的类型 ('CFG', 'DDG', 'CDG')
        """
        self.id = target_id
        self.label = label
        self.type = edge_type
        self.token = []  # 用于DDG边的变量信息


class Graph:
    """程序分析图"""
    
    def __init__(self):
        """初始化图"""
        self.nodes: List[Node] = []
        self.edges: Dict[int, List[Edge]] = {}
        self.id_to_nodes: Dict[int, Node] = {}
        self.defs: Dict[int, Set[str]] = {}  # 节点ID -> 定义的变量集合
        self.uses: Dict[int, Set[str]] = {}  # 节点ID -> 使用的变量集合
    
    def add_node(self, node: Node):
        """添加节点"""
        if node.id not in self.id_to_nodes:
            self.nodes.append(node)
            self.id_to_nodes[node.id] = node
            self.edges[node.id] = []
            self.defs[node.id] = node.defs
            self.uses[node.id] = node.uses
    
    def add_edge(self, edge_info):
        """添加边"""
        if isinstance(edge_info, tuple) and len(edge_info) == 2:
            # (source_node, target_edge)格式
            source_node, target_edge = edge_info
            if isinstance(source_node, Node):
                self.add_node(source_node)
                if isinstance(target_edge, list):
                    self.edges[source_node.id].extend(target_edge)
                else:
                    self.edges[source_node.id].append(target_edge)
    
    def get_def_use_info(self):
        """更新定义-使用信息"""
        for node in self.nodes:
            self.defs[node.id] = node.defs
            self.uses[node.id] = node.uses


class BaseAnalyzer:
    """基础分析器"""
    
    def __init__(self, language: str = "c"):
        """
        初始化分析器
        Args:
            language: 编程语言 ("c" 或 "cpp")
        """
        if language == "c":
            self.language = Language(tsc.language(), "c")
        elif language == "cpp":
            self.language = Language(tscpp.language(), "cpp")
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        self.parser = Parser()
        self.parser.set_language(self.language)
        self.language_name = language
    
    def parse_code(self, code: str):
        """解析代码"""
        tree = self.parser.parse(bytes(code, 'utf-8'))
        return tree.root_node
    
    def check_syntax(self, code: str) -> bool:
        """检查语法错误"""
        try:
            tree = self.parser.parse(bytes(code, 'utf-8'))
            return tree.root_node.has_error
        except:
            return True
    
    def find_functions(self, root_node):
        """查找所有函数定义"""
        functions = []
        
        def traverse(node):
            if node.type == 'function_definition':
                functions.append(node)
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return functions


def visualize_cfg(cfgs: List[Graph], filename: str = 'CFG', pdf: bool = True, dot_format: bool = True, view: bool = False):
    """可视化CFG"""
    dot = Digraph(comment=filename, strict=True)
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    dot.attr('edge', fontname='Arial')

    for cfg in cfgs:
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

    return dot


def visualize_ddg(ddgs: List[Graph], filename: str = 'DDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
    """可视化DDG"""
    dot = Digraph(comment=filename, strict=True)
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    dot.attr('edge', fontname='Arial')

    for ddg in ddgs:
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
                    source_id = edge.id
                    target_id = node_id
                    var_label = ', '.join(edge.token) if edge.token else ''
                    dot.edge(str(source_id), str(target_id),
                            label=var_label, style='dotted', color='red')

    # 保存.dot文件
    if dot_format:
        with open(f"{filename}.dot", 'w') as f:
            f.write(dot.source)

    # 生成PDF文件
    if pdf:
        dot.render(filename, view=view, cleanup=True)

    return dot


def visualize_pdg(pdgs: List[Graph], filename: str = 'PDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
    """可视化PDG"""
    dot = Digraph(comment=filename, strict=True)
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    dot.attr('edge', fontname='Arial')

    for pdg in pdgs:
        # 添加节点
        for node in pdg.nodes:
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

        # 添加边
        for node_id, edges in pdg.edges.items():
            for edge in edges:
                source_id = edge.id
                target_id = node_id

                if edge.type == 'DDG':
                    # 数据依赖边：红色虚线
                    var_label = ', '.join(edge.token) if edge.token else ''
                    dot.edge(str(source_id), str(target_id),
                            label=var_label, style='dotted', color='red')
                elif edge.type == 'CDG':
                    # 控制依赖边：蓝色实线
                    dot.edge(str(source_id), str(target_id),
                            color='blue', style='solid')
                else:
                    # 控制流边：黑色实线
                    label = edge.label if edge.label else ''
                    dot.edge(str(source_id), str(target_id), label=label)

    # 保存.dot文件
    if dot_format:
        with open(f"{filename}.dot", 'w') as f:
            f.write(dot.source)

    # 生成PDF文件
    if pdf:
        dot.render(filename, view=view, cleanup=True)

    return dot
