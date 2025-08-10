#!/usr/bin/env python3
"""
可视化模块

提供各种图的可视化功能
"""

from typing import List
from graphviz import Digraph
import html
from .graph import Graph, EdgeType


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
                # 只显示源代码，不显示节点类型
                code_label = html.escape(node.text)
                label = f"<{code_label}<SUB>{node.line}</SUB>>"
                if node.is_branch:
                    dot.node(str(node.id), shape='diamond', label=label)
                else:
                    dot.node(str(node.id), shape='rectangle', label=label)

        for edge in cfg.edges:
            if edge.source_node and edge.target_node:
                source_id = edge.source_node.id
                target_id = edge.target_node.id
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
                # 只显示源代码，不显示节点类型
                code_label = html.escape(node.text)
                label = f"<{code_label}<SUB>{node.line}</SUB>>"
                if node.is_branch:
                    dot.node(str(node.id), shape='diamond', label=label)
                else:
                    dot.node(str(node.id), shape='rectangle', label=label)

        # 添加数据依赖边
        for edge in ddg.edges:
            if edge.type == EdgeType.DDG and edge.source_node and edge.target_node:
                source_id = edge.source_node.id  # 源节点（定义/写入变量的节点）
                target_id = edge.target_node.id  # 目标节点（使用变量的节点）
                var_label = ', '.join(edge.token) if hasattr(edge, 'token') and edge.token else ''
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
            # 对于函数定义，显示完整签名（作为根节点，特别突出）
            if node.type == 'function_definition':
                label = f"<<B>ROOT</B><BR/>{html.escape(node.text)}<SUB>{node.line}</SUB>>"
                dot.node(str(node.id), label=label, shape='ellipse', style='filled', 
                        fillcolor='lightgreen', fontsize='14', width='2.0')
            else:
                # 只显示源代码，不显示节点类型
                code_label = html.escape(node.text)
                label = f"<{code_label}<SUB>{node.line}</SUB>>"
                if node.is_branch:
                    dot.node(str(node.id), shape='diamond', label=label, style='filled', fillcolor='yellow')
                else:
                    dot.node(str(node.id), shape='rectangle', label=label)

        # 添加边
        for edge in pdg.edges:
            if edge.type == EdgeType.DDG and edge.source_node and edge.target_node:
                # 数据依赖边：红色虚线
                source_id = edge.source_node.id  # 定义节点
                target_id = edge.target_node.id  # 使用节点
                var_label = ', '.join(edge.token) if hasattr(edge, 'token') and edge.token else ''
                dot.edge(str(source_id), str(target_id),
                        label=var_label, style='dotted', color='red')
            elif edge.type == EdgeType.CDG and edge.source_node and edge.target_node:
                # 控制依赖边：根据标签设置不同样式
                source_id = edge.source_node.id  # 控制节点
                target_id = edge.target_node.id  # 被控制节点
                
                # 根据边的标签设置不同的样式
                if edge.label == 'entry':
                    # 函数入口到普通节点：绿色粗线
                    dot.edge(str(source_id), str(target_id), 
                            color='green', style='solid', penwidth='2', 
                            label='entry')
                elif edge.label == 'branch':
                    # 函数入口到分支节点：橙色粗线
                    dot.edge(str(source_id), str(target_id), 
                            color='orange', style='solid', penwidth='2', 
                            label='branch')
                else:
                    # 分支控制依赖：蓝色实线
                    dot.edge(str(source_id), str(target_id), 
                            color='blue', style='solid', penwidth='1')
            elif edge.source_node and edge.target_node:
                # 控制流边：黑色实线
                source_id = edge.source_node.id
                target_id = edge.target_node.id
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


def visualize_cdg(cdgs: List[Graph], filename: str = 'CDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
    """可视化控制依赖图"""
    dot = Digraph(comment=filename, strict=True)
    dot.attr(rankdir='TB')
    dot.attr('node', fontname='Arial')
    dot.attr('edge', fontname='Arial')

    for cdg in cdgs:
        # 添加节点
        for node in cdg.nodes:
            # 对于函数定义，显示完整签名（作为根节点，特别突出）
            if node.type == 'function_definition':
                label = f"<<B>ROOT</B><BR/>{html.escape(node.text)}<SUB>{node.line}</SUB>>"
                dot.node(str(node.id), label=label, shape='ellipse', style='filled', 
                        fillcolor='lightgreen', fontsize='14', width='2.0')
            else:
                # 只显示源代码，不显示节点类型
                code_label = html.escape(node.text)
                label = f"<{code_label}<SUB>{node.line}</SUB>>"
                if node.is_branch:
                    dot.node(str(node.id), shape='diamond', label=label, style='filled', fillcolor='yellow')
                else:
                    dot.node(str(node.id), shape='rectangle', label=label)

        # 添加控制依赖边
        for edge in cdg.edges:
            if edge.type == EdgeType.CDG and edge.source_node and edge.target_node:
                # 控制依赖边：从控制节点指向依赖节点
                source_id = edge.source_node.id  # 控制节点
                target_id = edge.target_node.id  # 被控制节点
                
                # 根据边的标签设置不同的样式
                if edge.label == 'entry':
                    # 函数入口到普通节点：绿色粗线
                    dot.edge(str(source_id), str(target_id), 
                            color='green', style='solid', penwidth='2', 
                            label='entry')
                elif edge.label == 'branch':
                    # 函数入口到分支节点：橙色粗线
                    dot.edge(str(source_id), str(target_id), 
                            color='orange', style='solid', penwidth='2', 
                            label='branch')
                else:
                    # 分支控制依赖：蓝色实线
                    dot.edge(str(source_id), str(target_id), 
                            color='blue', style='solid', penwidth='1')

    # 保存.dot文件
    if dot_format:
        with open(f"{filename}.dot", 'w') as f:
            f.write(dot.source)

    # 生成PDF文件
    if pdf:
        dot.render(filename, view=view, cleanup=True)

    return dot
