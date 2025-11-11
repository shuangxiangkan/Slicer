#!/usr/bin/env python3
"""
程序切片工具

基于PDG/DDG进行后向切片，提取与目标函数调用相关的代码
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import Set, List, Optional
from analysis import PDG, Node
from analysis.utils import text

# 配置日志
logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO, format_string=None):
    """
    配置日志记录
    
    Args:
        level: 日志级别 (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
        format_string: 自定义日志格式字符串
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 为slice模块设置日志级别
    slice_logger = logging.getLogger('slice')
    slice_logger.setLevel(level)


class FunctionSlicer:
    """函数切片器 - 提取与目标函数调用相关的代码"""
    
    def __init__(self, language: str = "c"):
        """
        初始化切片器
        Args:
            language: 编程语言 ("c" 或 "cpp")
        """
        self.language = language
        self.pdg_builder = PDG(language)
    
    def slice_by_function_call(self, source_code: str, target_function: str) -> Optional[str]:
        """
        对函数进行切片，提取与目标函数调用相关的代码
        
        Args:
            source_code: 源函数代码
            target_function: 目标函数名
            
        Returns:
            切片后的代码，如果没有找到目标函数调用则返回None
        """
        # 1. 构建PDG
        pdg = self.pdg_builder.construct_pdg(source_code)
        if not pdg:
            logger.warning("无法构建PDG")
            return None
        
        # 2. 找到所有调用目标函数的节点
        call_nodes = self._find_function_calls(pdg, target_function)
        if not call_nodes:
            logger.warning(f"未找到对函数 '{target_function}' 的调用")
            return None
        
        logger.info(f"找到 {len(call_nodes)} 个对 '{target_function}' 的调用")
        
        # 3. 从调用点进行后向切片（找影响调用的语句）
        backward_nodes = self._backward_slice(pdg, call_nodes)
        
        # 4. 从调用点进行前向切片（找使用返回值的语句）
        forward_nodes = self._forward_slice(pdg, call_nodes)
        
        # 5. 对前向切片的结果进行后向切片（找到前向节点依赖的变量定义）
        forward_list = list(forward_nodes - backward_nodes)  # 排除已在后向切片中的节点
        forward_deps = self._backward_slice(pdg, forward_list) if forward_list else set()
        
        # 6. 合并所有切片结果
        relevant_nodes = backward_nodes.union(forward_nodes).union(forward_deps)
        
        logger.info(f"切片得到 {len(relevant_nodes)} 个相关节点 (后向: {len(backward_nodes)}, 前向: {len(forward_nodes)}, 前向依赖: {len(forward_deps)})")
        
        # 7. 提取切片代码
        sliced_code = self._extract_code(source_code, relevant_nodes)
        
        return sliced_code
    
    def _find_function_calls(self, pdg, target_function: str) -> List[Node]:
        """查找所有调用目标函数的节点"""
        call_nodes = []
        
        for node in pdg.nodes:
            # 检查节点文本中是否包含对目标函数的调用
            if self._is_calling_function(node, target_function):
                call_nodes.append(node)
        
        return call_nodes
    
    def _is_calling_function(self, node: Node, function_name: str) -> bool:
        """检查节点是否调用了指定函数"""
        # 简单的文本匹配：查找 "function_name("
        node_text = node.text.strip()
        return f"{function_name}(" in node_text
    
    def _backward_slice(self, pdg, start_nodes: List[Node]) -> Set[Node]:
        """
        从起始节点进行后向切片
        
        后向切片：找出所有影响起始节点的语句
        沿着依赖边反向遍历
        """
        relevant_nodes = set()
        visited = set()
        
        def traverse_backward(node: Node, depth=0):
            if node.id in visited:
                return
            visited.add(node.id)
            relevant_nodes.add(node)
            
            # 查找所有指向当前节点的边（数据依赖和控制依赖）
            incoming_edges = 0
            for edge in pdg.edges:
                if edge.target_node and edge.target_node.id == node.id:
                    incoming_edges += 1
                    # 沿着依赖边反向遍历
                    if edge.source_node:
                        traverse_backward(edge.source_node, depth + 1)
        
        # 从所有调用点开始后向遍历
        for call_node in start_nodes:
            traverse_backward(call_node)
        
        return relevant_nodes
    
    def _forward_slice(self, pdg, start_nodes: List[Node]) -> Set[Node]:
        """
        从起始节点进行前向切片
        
        前向切片：找出所有依赖起始节点的语句
        沿着依赖边正向遍历
        """
        relevant_nodes = set()
        visited = set()
        
        def traverse_forward(node: Node, depth=0):
            if node.id in visited:
                return
            visited.add(node.id)
            relevant_nodes.add(node)
            
            # 查找所有从当前节点出发的边（数据依赖和控制依赖）
            outgoing_edges = 0
            for edge in pdg.edges:
                if edge.source_node and edge.source_node.id == node.id:
                    outgoing_edges += 1
                    # 沿着依赖边正向遍历
                    if edge.target_node:
                        traverse_forward(edge.target_node, depth + 1)
        
        # 从所有调用点开始前向遍历
        for call_node in start_nodes:
            traverse_forward(call_node)
        
        return relevant_nodes
    
    def _collect_variable_declarations(self, pdg, nodes: Set[Node]) -> Set[Node]:
        """
        收集切片中使用的变量的声明节点
        
        变量声明节点通常是只有 defs 而没有 uses 的节点
        （例如：int x; 定义了 x 但不使用任何变量）
        """
        # 收集切片中所有使用和定义的变量
        used_vars = set()
        defined_vars = set()
        
        for node in nodes:
            if hasattr(node, 'uses') and node.uses:
                used_vars.update(node.uses)
            if hasattr(node, 'defs') and node.defs:
                defined_vars.update(node.defs)
        
        # 所有需要的变量
        needed_vars = used_vars.union(defined_vars)
        
        # 在PDG中找到这些变量的声明节点
        declaration_nodes = set()
        for node in pdg.nodes:
            if node.type == 'function_definition':
                continue
            
            # 变量声明节点的特征：
            # 1. 有 defs（定义了变量）
            # 2. 没有 uses 或 uses 为空（不使用其他变量）
            # 3. 定义的变量在需要的变量集合中
            if hasattr(node, 'defs') and node.defs:
                has_uses = hasattr(node, 'uses') and node.uses
                
                # 如果这是一个纯声明节点（没有使用其他变量）
                if not has_uses:
                    # 检查它定义的变量是否被需要
                    if node.defs.intersection(needed_vars):
                        declaration_nodes.add(node)
        
        return declaration_nodes
    
    def _extract_code(self, source_code: str, nodes: Set[Node]) -> str:
        """
        从源代码中提取相关节点的代码
        
        策略：
        1. 获取函数签名（始终保留）
        2. 收集变量声明节点
        3. 按行号排序节点
        4. 提取相关语句
        """
        if not nodes:
            return ""
        
        # 解析源代码获取AST
        root_node = self.pdg_builder.parse_code(source_code)
        
        # 查找函数定义
        functions = self.pdg_builder.find_functions(root_node)
        if not functions:
            return source_code
        
        # 假设只有一个函数（单函数版本）
        func_node = functions[0]
        
        # 获取函数签名
        func_signature = self._get_function_signature(func_node)
        
        # 收集变量声明节点
        pdg = self.pdg_builder.pdg
        if pdg:
            declaration_nodes = self._collect_variable_declarations(pdg, nodes)
            # 将声明节点加入到切片中
            nodes = nodes.union(declaration_nodes)
        
        # 收集相关节点的行号
        relevant_lines = set()
        for node in nodes:
            if node.type != 'function_definition':  # 跳过函数定义节点本身
                relevant_lines.add(node.line)
        
        # 提取代码行
        lines = source_code.split('\n')
        sliced_lines = []
        
        # 添加函数签名
        sliced_lines.append(func_signature + " {")
        
        # 添加相关的语句
        for i, line in enumerate(lines, 1):
            if i in relevant_lines:
                # 保留缩进
                stripped = line.lstrip()
                if stripped and not stripped.startswith('}'):
                    sliced_lines.append("    " + stripped)
        
        # 闭合函数
        sliced_lines.append("}")
        
        return '\n'.join(sliced_lines)
    
    def _get_function_signature(self, func_node) -> str:
        """获取函数签名"""
        # 获取返回类型
        type_node = func_node.child_by_field_name('type')
        declarator = func_node.child_by_field_name('declarator')
        
        if type_node and declarator:
            return_type = text(type_node)
            func_declarator = text(declarator)
            return f"{return_type} {func_declarator}"
        elif declarator:
            return text(declarator)
        else:
            return "void function()"

def main():
    """命令行用法: python slicer.py <源文件路径> <目标函数名>"""
    # 配置日志输出
    setup_logging(level=logging.INFO)
    
    # 检查命令行参数
    if len(sys.argv) != 3:
        print("用法: python slicer.py <源文件路径> <目标函数名>")
        print("示例: python slicer.py example.c gzclose")
        print("注意: 输入文件必须只包含一个函数定义，不能包含多个函数")
        sys.exit(1)
    
    source_file = sys.argv[1]
    target_function = sys.argv[2]
    
    # 读取源文件
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        logger.error(f"文件不存在: {source_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        sys.exit(1)
    
    # 创建切片器
    slicer = FunctionSlicer(language="c")
    
    # 执行切片
    logger.info("=" * 60)
    logger.info(f"对文件 '{source_file}' 中的函数 '{target_function}' 进行切片:")
    logger.info("=" * 60)
    sliced = slicer.slice_by_function_call(source_code, target_function)
    
    if sliced:
        print(sliced)
    else:
        logger.error("切片失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
