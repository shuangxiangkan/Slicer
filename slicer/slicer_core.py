#!/usr/bin/env python3
"""
C/C++ 函数程序切片核心实现
"""

import tree_sitter
from tree_sitter import Language
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
import networkx as nx
import re
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional

from .models import SliceType, ParameterSliceResult, Variable, Statement


class CFunctionSlicer:
    """C/C++函数切片器"""
    
    def __init__(self, language: str = "c"):
        """
        初始化切片器
        
        Args:
            language: 语言类型，"c" 或 "cpp"
        """
        self.language = language
        self.parser = tree_sitter.Parser()
        if language == "c":
            lang_capsule = tsc.language()
            language_obj = Language(lang_capsule, 'c')
            self.parser.set_language(language_obj)
        else:
            lang_capsule = tscpp.language()
            language_obj = Language(lang_capsule, 'cpp')
            self.parser.set_language(language_obj)
        
        # 依赖图
        self.dependency_graph = nx.DiGraph()
        
        # 语句列表
        self.statements = []
        
        # 变量定义和使用信息
        self.var_definitions = {}  # 变量名 -> 定义它的语句行号列表
        self.var_uses = {}         # 变量名 -> 使用它的语句行号列表
        
        # 函数信息
        self.function_parameters = []  # 函数参数列表
        self.return_statements = []    # 返回语句列表
    
    def parse_function(self, code: str, function_name: str) -> Optional[tree_sitter.Node]:
        """
        解析代码中的指定函数
        
        Args:
            code: 源代码
            function_name: 函数名
            
        Returns:
            函数节点或None
        """
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        def find_function(node: tree_sitter.Node) -> Optional[tree_sitter.Node]:
            if node.type == "function_definition":
                # 查找函数名
                for child in node.children:
                    if child.type == "function_declarator":
                        # 在function_declarator中查找identifier
                        for grandchild in child.children:
                            if grandchild.type == "identifier":
                                if grandchild.text.decode("utf8") == function_name:
                                    return node
                    elif child.type == "identifier":
                        if child.text.decode("utf8") == function_name:
                            return node
            
            # 递归查找子节点
            for child in node.children:
                result = find_function(child)
                if result:
                    return result
            
            return None
        
        return find_function(root_node)
    
    def extract_function_parameters(self, function_node: tree_sitter.Node) -> List[str]:
        """
        提取函数参数
        
        Args:
            function_node: 函数节点
            
        Returns:
            参数名列表
        """
        parameters = []
        
        def find_parameters(node: tree_sitter.Node):
            if node.type == "parameter_declaration":
                # 查找参数名
                for child in node.children:
                    if child.type == "identifier":
                        parameters.append(child.text.decode("utf8"))
            elif node.type == "parameter_list":
                for child in node.children:
                    find_parameters(child)
            else:
                for child in node.children:
                    find_parameters(child)
        
        find_parameters(function_node)
        return parameters
    
    def extract_variables_from_node(self, node: tree_sitter.Node) -> Tuple[Set[str], Set[str]]:
        """
        从节点中提取变量的定义和使用信息
        
        Args:
            node: 语法树节点
            
        Returns:
            (定义的变量集合, 使用的变量集合)
        """
        defined_vars = set()
        used_vars = set()
        
        def traverse(n: tree_sitter.Node, in_assignment_left: bool = False):
            if n.type == "identifier":
                var_name = n.text.decode("utf8")
                if in_assignment_left:
                    defined_vars.add(var_name)
                else:
                    used_vars.add(var_name)
            elif n.type == "assignment_expression":
                # 赋值表达式：左边是定义，右边是使用
                if len(n.children) >= 3:
                    left_child = n.children[0]
                    right_child = n.children[2]
                    traverse(left_child, True)
                    traverse(right_child, False)
                else:
                    for child in n.children:
                        traverse(child, in_assignment_left)
            elif n.type in ["init_declarator", "declaration"]:
                # 变量声明
                for child in n.children:
                    if child.type == "identifier":
                        defined_vars.add(child.text.decode("utf8"))
                    elif child.type == "init_declarator":
                        # 处理初始化声明
                        for grandchild in child.children:
                            if grandchild.type == "identifier":
                                defined_vars.add(grandchild.text.decode("utf8"))
                            else:
                                traverse(grandchild, False)
                    else:
                        traverse(child, False)
            else:
                for child in n.children:
                    traverse(child, in_assignment_left)
        
        traverse(node)
        return defined_vars, used_vars

    def analyze_function(self, code: str, function_name: str):
        """
        分析函数，构建依赖图
        
        Args:
            code: 源代码
            function_name: 函数名
        """
        # 清理之前的分析结果
        self.dependency_graph.clear()
        self.statements.clear()
        self.var_definitions.clear()
        self.var_uses.clear()
        self.function_parameters.clear()
        self.return_statements.clear()
        
        # 解析函数
        function_node = self.parse_function(code, function_name)
        if not function_node:
            raise ValueError(f"函数 '{function_name}' 未找到")
        
        # 提取函数参数
        self.function_parameters = self.extract_function_parameters(function_node)
        
        # 找到函数体
        compound_statement = None
        for child in function_node.children:
            if child.type == "compound_statement":
                compound_statement = child
                break
        
        if not compound_statement:
            raise ValueError(f"函数 '{function_name}' 没有函数体")
        
        # 分析语句
        lines = code.split('\n')
        self._analyze_statements(compound_statement, lines)
        
        # 构建依赖图
        self._build_dependency_graph()
    
    def _analyze_statements(self, compound_statement: tree_sitter.Node, lines: List[str]):
        """
        分析函数体中的语句
        
        Args:
            compound_statement: 复合语句节点
            lines: 代码行列表
        """
        def analyze_node(node: tree_sitter.Node):
            # 获取语句的行号和代码
            start_row = node.start_point[0] + 1  # tree-sitter的行号从0开始
            end_row = node.end_point[0] + 1
            
            # 提取该语句的代码
            if start_row <= len(lines):
                if start_row == end_row:
                    code_text = lines[start_row - 1].strip()
                else:
                    code_text = '\n'.join(lines[start_row - 1:end_row]).strip()
            else:
                code_text = ""
            
            # 提取变量信息
            defined_vars, used_vars = self.extract_variables_from_node(node)
            
            # 创建语句对象
            stmt = Statement(
                line=start_row,
                code=code_text,
                node=node,
                variables_defined=defined_vars,
                variables_used=used_vars
            )
            
            self.statements.append(stmt)
            
            # 记录变量定义和使用信息
            for var in defined_vars:
                if var not in self.var_definitions:
                    self.var_definitions[var] = []
                self.var_definitions[var].append(start_row)
            
            for var in used_vars:
                if var not in self.var_uses:
                    self.var_uses[var] = []
                self.var_uses[var].append(start_row)
            
            # 记录返回语句
            if node.type == "return_statement":
                self.return_statements.append(stmt)
        
        # 遍历所有语句
        def traverse_statements(node: tree_sitter.Node):
            if node.type in ["expression_statement", "declaration", "if_statement", 
                           "while_statement", "for_statement", "return_statement",
                           "assignment_expression"]:
                analyze_node(node)
            else:
                for child in node.children:
                    traverse_statements(child)
        
        traverse_statements(compound_statement)
    
    def _build_dependency_graph(self):
        """构建变量依赖图"""
        # 为每个语句添加节点
        for stmt in self.statements:
            self.dependency_graph.add_node(stmt.line)
        
        # 添加依赖边
        for stmt in self.statements:
            for used_var in stmt.variables_used:
                # 找到定义这个变量的语句
                if used_var in self.var_definitions:
                    for def_line in self.var_definitions[used_var]:
                        if def_line < stmt.line:  # 只考虑在当前语句之前的定义
                            self.dependency_graph.add_edge(def_line, stmt.line)

    def slice_function(self, target_variable: str, target_line: int, 
                      slice_type: SliceType = SliceType.BACKWARD) -> List[int]:
        """
        对函数进行程序切片
        
        Args:
            target_variable: 目标变量名
            target_line: 目标行号
            slice_type: 切片类型
            
        Returns:
            切片包含的行号列表
        """
        if slice_type == SliceType.BACKWARD:
            return self._backward_slice(target_variable, target_line)
        elif slice_type == SliceType.FORWARD:
            return self._forward_slice(target_variable, target_line)
        else:
            raise ValueError(f"不支持的切片类型: {slice_type}")
    
    def _backward_slice(self, target_variable: str, target_line: int) -> List[int]:
        """执行后向切片"""
        slice_lines = set()
        
        def dfs(line: int, visited: Set[int]):
            if line in visited:
                return
            visited.add(line)
            slice_lines.add(line)
            
            # 查找所有影响当前行的前驱节点
            for pred in self.dependency_graph.predecessors(line):
                dfs(pred, visited)
        
        dfs(target_line, set())
        return sorted(list(slice_lines))
    
    def _forward_slice(self, target_variable: str, target_line: int) -> List[int]:
        """执行前向切片"""
        slice_lines = set()
        
        def dfs(line: int, visited: Set[int]):
            if line in visited:
                return
            visited.add(line)
            slice_lines.add(line)
            
            # 查找所有被当前行影响的后继节点
            for succ in self.dependency_graph.successors(line):
                dfs(succ, visited)
        
        dfs(target_line, set())
        return sorted(list(slice_lines))

    def perform_parameter_slice_analysis(self, code: str) -> ParameterSliceResult:
        """
        执行参数切片分析
        
        Args:
            code: 源代码
            
        Returns:
            参数切片分析结果
        """
        result = ParameterSliceResult()
        result.function_parameters = self.function_parameters.copy()
        
        lines = code.split('\n')
        
        # 1. 对每个参数进行前向切片（找到参数影响的所有语句）
        for param in self.function_parameters:
            # 找到参数首次使用的位置（通常是参数声明行，但在函数体中查找）
            param_start_lines = []
            for stmt in self.statements:
                if param in stmt.variables_used and param not in stmt.variables_defined:
                    param_start_lines.append(stmt.line)
            
            if param_start_lines:
                # 使用第一个使用该参数的语句进行前向切片
                forward_slice = self._forward_slice(param, min(param_start_lines))
                result.parameter_slices[param] = forward_slice
            else:
                result.parameter_slices[param] = []
        
        # 2. 对返回值进行后向切片（找到影响返回值的所有语句）
        if self.return_statements:
            # 合并所有返回语句的后向切片
            all_return_slices = set()
            for return_stmt in self.return_statements:
                backward_slice = self._backward_slice("", return_stmt.line)
                all_return_slices.update(backward_slice)
            result.return_slice = sorted(list(all_return_slices))
        
        # 3. 分析参数间的交互（参数A影响参数B的情况）
        for param1 in self.function_parameters:
            for param2 in self.function_parameters:
                if param1 != param2:
                    # 检查param1的前向切片是否包含重新定义param2的语句
                    param1_slice = result.parameter_slices.get(param1, [])
                    param2_redefinition_lines = []
                    
                    for stmt in self.statements:
                        if stmt.line in param1_slice and param2 in stmt.variables_defined:
                            param2_redefinition_lines.append(stmt.line)
                    
                    if param2_redefinition_lines:
                        if param1 not in result.parameter_interactions:
                            result.parameter_interactions[param1] = {}
                        result.parameter_interactions[param1][param2] = param2_redefinition_lines
        
        # 4. 生成切片代码片段
        result.slice_code_snippets = self._generate_slice_code_snippets(code, result)
        
        return result
    
    def _generate_slice_code_snippets(self, code: str, result: ParameterSliceResult) -> Dict[str, str]:
        """
        生成切片代码片段
        
        Args:
            code: 原始代码
            result: 参数切片结果
            
        Returns:
            切片代码片段字典
        """
        lines = code.split('\n')
        snippets = {}
        
        # 为每个参数生成前向切片代码
        for param, slice_lines in result.parameter_slices.items():
            if slice_lines:
                snippet_lines = []
                snippet_lines.append(f"// 参数 '{param}' 的前向切片（该参数影响的代码）")
                snippet_lines.append("// " + "=" * 50)
                for line_num in slice_lines:
                    if 1 <= line_num <= len(lines):
                        snippet_lines.append(f"/* 行{line_num:3d} */ {lines[line_num-1]}")
                snippets[f"param_{param}_forward"] = "\n".join(snippet_lines)
        
        # 生成返回值后向切片代码
        if result.return_slice:
            snippet_lines = []
            snippet_lines.append("// 返回值的后向切片（影响返回值的代码）")
            snippet_lines.append("// " + "=" * 50)
            for line_num in result.return_slice:
                if 1 <= line_num <= len(lines):
                    snippet_lines.append(f"/* 行{line_num:3d} */ {lines[line_num-1]}")
            snippets["return_backward"] = "\n".join(snippet_lines)
        
        # 生成参数间交互代码
        for param1, interactions in result.parameter_interactions.items():
            for param2, interaction_lines in interactions.items():
                snippet_lines = []
                snippet_lines.append(f"// 参数 '{param1}' 影响参数 '{param2}' 的代码")
                snippet_lines.append("// " + "=" * 50)
                for line_num in interaction_lines:
                    if 1 <= line_num <= len(lines):
                        snippet_lines.append(f"/* 行{line_num:3d} */ {lines[line_num-1]}")
                snippets[f"param_{param1}_affects_{param2}"] = "\n".join(snippet_lines)
        
        return snippets 