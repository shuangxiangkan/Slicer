#!/usr/bin/env python3
"""
函数级变量切片工具 - 对C/C++函数体进行变量相关代码切片
输入：函数体源码字符串、变量名
输出：与该变量相关的所有代码段（保证语法完整性）
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node
from typing import List, Optional, Set, Dict
import logging
import re
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class FunctionLevelSlicer:
    """函数级变量切片器"""
    
    def __init__(self, language: str = "c"):
        """初始化切片器"""
        self.language = language
        if language == "cpp":
            self.lang = Language(tscpp.language(), "cpp")
        else:
            self.lang = Language(tsc.language(), "c")
        
        self.parser = Parser()
        self.parser.set_language(self.lang)
    
    def slice_function_by_variable(self, function_code: str, variable: str,
                                   function_name: str = None, save_to_file: bool = False) -> str:
        """
        对函数体进行变量相关切片
        Args:
            function_code: 函数体源码字符串
            variable: 变量名
            function_name: 函数名（用于保存文件）
            save_to_file: 是否保存到文件
        Returns:
            与变量相关的代码片段字符串（包含函数签名和大括号）
        """
        tree = self.parser.parse(function_code.encode("utf-8"))
        root = tree.root_node

        # 收集相关节点的行号
        related_lines = set()

        # 递归查找变量相关的节点
        self._find_variable_related_nodes(root, variable, related_lines, function_code)

        # 扩展相关行以保证语法完整性
        extended_lines = self._extend_for_syntax_completeness(related_lines, function_code)

        # 添加依赖变量的定义
        extended_lines = self._add_dependency_definitions(extended_lines, function_code)

        # 提取函数签名和构建完整的切片结果
        slice_result = self._build_complete_function_slice(function_code, extended_lines)

        # 如果需要保存到文件
        if save_to_file and function_name:
            self._save_slice_results(function_code, slice_result, function_name, variable)

        return slice_result
    
    def _find_variable_related_nodes(self, node: Node, variable: str, related_lines: Set[int], source_code: str):
        """递归查找与变量相关的AST节点"""
        
        # 检查当前节点是否包含目标变量
        if self._node_contains_variable(node, variable, source_code):
            # 添加当前节点的所有行
            related_lines.update(range(node.start_point[0], node.end_point[0] + 1))
        
        # 递归处理子节点
        for child in node.children:
            self._find_variable_related_nodes(child, variable, related_lines, source_code)
    
    def _node_contains_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查节点是否包含目标变量"""
        
        # 变量声明节点
        if node.type == "declaration":
            return self._check_declaration_for_variable(node, variable, source_code)
        
        # 赋值表达式
        if node.type == "assignment_expression":
            return self._check_assignment_for_variable(node, variable, source_code)
        
        # 更新表达式 (++, --)
        if node.type == "update_expression":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 返回语句
        if node.type == "return_statement":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 控制流语句
        if node.type in ["if_statement", "while_statement", "for_statement", "switch_statement", "do_statement"]:
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 函数调用表达式
        if node.type == "call_expression":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 表达式语句
        if node.type == "expression_statement":
            return self._check_identifier_in_node(node, variable, source_code)
        
        return False
    
    def _check_declaration_for_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查声明节点是否包含目标变量"""
        # 查找声明器中的标识符
        for child in node.children:
            if child.type == "init_declarator":
                declarator = child.child_by_field_name("declarator")
                if declarator and declarator.type == "identifier":
                    name = source_code[declarator.start_byte:declarator.end_byte]
                    if name == variable:
                        return True
            elif child.type == "identifier":
                name = source_code[child.start_byte:child.end_byte]
                if name == variable:
                    return True
        return False
    
    def _check_assignment_for_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查赋值表达式是否包含目标变量"""
        # 检查左值和右值
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        
        # 检查左值
        if left and self._contains_identifier(left, variable, source_code):
            return True
        
        # 检查右值
        if right and self._contains_identifier(right, variable, source_code):
            return True
        
        return False
    
    def _check_identifier_in_node(self, node: Node, variable: str, source_code: str) -> bool:
        """检查节点中是否包含目标标识符"""
        return self._contains_identifier(node, variable, source_code)
    
    def _contains_identifier(self, node: Node, variable: str, source_code: str) -> bool:
        """递归检查节点及其子节点是否包含目标标识符"""
        if node.type == "identifier":
            name = source_code[node.start_byte:node.end_byte]
            if name == variable:
                return True
        
        # 递归检查子节点
        for child in node.children:
            if self._contains_identifier(child, variable, source_code):
                return True
        
        return False

    def _extend_for_syntax_completeness(self, related_lines: Set[int], source_code: str) -> Set[int]:
        """
        扩展相关行以保证语法完整性
        Args:
            related_lines: 已识别的相关行号集合
            source_code: 源代码字符串
        Returns:
            扩展后的行号集合
        """
        if not related_lines:
            return related_lines

        extended_lines = related_lines.copy()
        code_lines = source_code.splitlines()

        # 处理控制结构的完整性
        for line_num in list(related_lines):
            if line_num < len(code_lines):
                line = code_lines[line_num].strip()

                # 处理if语句的完整性
                if line.startswith('if') and line.endswith('{'):
                    extended_lines.update(self._find_matching_braces(line_num, code_lines))

                # 处理for/while循环的完整性
                elif (line.startswith('for') or line.startswith('while')) and line.endswith('{'):
                    extended_lines.update(self._find_matching_braces(line_num, code_lines))

                # 处理switch语句的完整性
                elif line.startswith('switch') and line.endswith('{'):
                    extended_lines.update(self._find_matching_braces(line_num, code_lines))

                # 处理函数调用的完整性（多行参数）
                elif '(' in line and not line.rstrip().endswith(';'):
                    extended_lines.update(self._find_statement_end(line_num, code_lines))

        return extended_lines

    def _find_matching_braces(self, start_line: int, code_lines: List[str]) -> Set[int]:
        """查找匹配的大括号范围"""
        brace_lines = set()
        brace_count = 0

        for i in range(start_line, len(code_lines)):
            line = code_lines[i]
            brace_lines.add(i)

            # 计算大括号
            brace_count += line.count('{') - line.count('}')

            if brace_count == 0 and i > start_line:
                break

        return brace_lines

    def _find_statement_end(self, start_line: int, code_lines: List[str]) -> Set[int]:
        """查找语句结束位置"""
        statement_lines = set()

        for i in range(start_line, len(code_lines)):
            line = code_lines[i]
            statement_lines.add(i)

            if line.rstrip().endswith(';'):
                break

        return statement_lines

    def _add_dependency_definitions(self, related_lines: Set[int], source_code: str) -> Set[int]:
        """
        递归添加依赖变量的定义行
        Args:
            related_lines: 已识别的相关行号集合
            source_code: 源代码字符串
        Returns:
            包含依赖定义的扩展行号集合
        """
        extended_lines = related_lines.copy()
        code_lines = source_code.splitlines()

        # 递归查找依赖，直到没有新的依赖为止
        changed = True
        iteration = 0
        max_iterations = 10  # 防止无限循环

        while changed and iteration < max_iterations:
            changed = False
            old_size = len(extended_lines)
            iteration += 1

            # 提取当前切片中使用的变量
            used_variables = set()
            for line_num in extended_lines:
                if line_num < len(code_lines):
                    line = code_lines[line_num]
                    # 提取标识符
                    import re
                    identifiers = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', line)
                    for identifier in identifiers:
                        # 过滤掉C/C++关键字和常见类型
                        if not self._is_keyword_or_builtin_type(identifier):
                            used_variables.add(identifier)

            # 查找这些变量的定义
            for line_num, line in enumerate(code_lines):
                if line_num not in extended_lines:
                    # 查找变量声明
                    for var in used_variables:
                        if self._is_variable_declaration(line, var):
                            extended_lines.add(line_num)
                            changed = True

            # 检查是否有新的行被添加
            if len(extended_lines) == old_size:
                changed = False

        return extended_lines

    def _is_keyword_or_builtin_type(self, identifier: str) -> bool:
        """
        检查标识符是否为C/C++关键字或内置类型
        Args:
            identifier: 要检查的标识符
        Returns:
            如果是关键字或内置类型返回True，否则返回False
        """
        # C/C++关键字
        keywords = {
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
            'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
            'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static',
            'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile', 'while',
            # C++关键字
            'class', 'private', 'protected', 'public', 'virtual', 'inline', 'template',
            'typename', 'namespace', 'using', 'try', 'catch', 'throw', 'new', 'delete',
            'this', 'operator', 'friend', 'explicit', 'mutable', 'bool', 'true', 'false',
            # 常见类型
            'size_t', 'ptrdiff_t', 'wchar_t', 'NULL'
        }

        # 常见的宏和修饰符
        common_macros = {
            'EXPORT', 'INLINE', 'STATIC', 'EXTERN', 'CONST', 'VOLATILE',
            'RESTRICT', 'NORETURN', 'DEPRECATED', 'UNUSED', 'PACKED'
        }

        return identifier in keywords or identifier in common_macros

    def _is_variable_declaration(self, line: str, var_name: str) -> bool:
        """
        检查一行代码是否包含指定变量的声明
        Args:
            line: 代码行
            var_name: 变量名
        Returns:
            如果包含变量声明返回True，否则返回False
        """
        import re

        # 清理行内容，去掉注释
        clean_line = re.sub(r'//.*$', '', line.strip())
        clean_line = re.sub(r'/\*.*?\*/', '', clean_line)

        # 如果行为空或只是注释，跳过
        if not clean_line.strip():
            return False

        # 通用的变量声明模式
        patterns = [
            # 基本模式：类型 变量名 [= 值];
            rf'\b[\w:]+\s+{re.escape(var_name)}\b\s*[=;,]',
            # 指针模式：类型 *变量名 [= 值];
            rf'\b[\w:]+\s*\*+\s*{re.escape(var_name)}\b\s*[=;,]',
            # 引用模式：类型 &变量名 [= 值];
            rf'\b[\w:]+\s*&\s*{re.escape(var_name)}\b\s*[=;,]',
            # 常量模式：const 类型 变量名 [= 值];
            rf'\bconst\s+[\w:]+\s+{re.escape(var_name)}\b\s*[=;,]',
            # 多个修饰符：static const 类型 变量名 [= 值];
            rf'\b(?:static|extern|inline|volatile|register|auto)\s+(?:[\w:]+\s+)*{re.escape(var_name)}\b\s*[=;,]',
            # 复杂类型：struct/union/enum 类型名 变量名;
            rf'\b(?:struct|union|enum|class)\s+[\w:]+\s+{re.escape(var_name)}\b\s*[=;,]',
            # 函数指针等复杂声明
            rf'\b[\w:]+\s*\(\s*\*\s*{re.escape(var_name)}\s*\)',
            # 模板类型：std::vector<int> 变量名;
            rf'\b[\w:]+<[^>]+>\s*[&*]*\s*{re.escape(var_name)}\b\s*[=;,]',
            # 多变量声明：int a, b, c;
            rf'\b[\w:]+\s+(?:\w+\s*,\s*)*{re.escape(var_name)}\b\s*[=;,]',
            # auto类型：auto 变量名 = 值;
            rf'\bauto\s+{re.escape(var_name)}\b\s*[=;]',
        ]

        for pattern in patterns:
            if re.search(pattern, clean_line):
                # 额外检查：确保不是函数调用或其他非声明语句
                if not self._is_likely_function_call_or_assignment(clean_line, var_name):
                    return True

        return False

    def _is_likely_function_call_or_assignment(self, line: str, var_name: str) -> bool:
        """
        检查是否可能是函数调用或赋值语句而非声明
        Args:
            line: 代码行
            var_name: 变量名
        Returns:
            如果可能是函数调用或赋值返回True
        """
        import re

        # 如果变量名前面有赋值操作符，可能是赋值而非声明
        if re.search(rf'{re.escape(var_name)}\s*=', line):
            # 检查是否在行首或类型声明后，如果是则可能是声明中的初始化
            if re.search(rf'^\s*[\w:]+\s+.*{re.escape(var_name)}\s*=', line):
                return False  # 这是声明中的初始化
            else:
                return True   # 这是赋值语句

        # 如果变量名后面紧跟括号，可能是函数调用
        if re.search(rf'{re.escape(var_name)}\s*\(', line):
            return True

        return False

    def _build_complete_function_slice(self, function_code: str, related_lines: Set[int]) -> str:
        """
        构建包含函数签名和大括号的完整切片结果
        Args:
            function_code: 原始函数代码
            related_lines: 相关行号集合
        Returns:
            完整的函数切片字符串
        """
        code_lines = function_code.splitlines()

        # 提取函数签名（第一行或前几行）
        signature_end_line = 0

        # 查找函数签名结束位置（遇到第一个 '{' ）
        for i, line in enumerate(code_lines):
            if '{' in line:
                signature_end_line = i
                break

        # 构建函数签名
        signature_lines = code_lines[:signature_end_line + 1]
        function_signature = "\n".join(signature_lines)

        # 构建切片后的函数体
        sliced_body_lines = []
        for i, line in enumerate(code_lines):
            if i in related_lines and i > signature_end_line:
                sliced_body_lines.append(line)

        # 如果没有切片内容，添加注释
        if not sliced_body_lines:
            sliced_body_lines = ["    // No relevant code found for the specified variable"]

        # 构建完整的函数
        result_lines = []

        # 添加函数签名（确保以 '{' 结尾）
        if not function_signature.rstrip().endswith('{'):
            function_signature = function_signature.rstrip() + " {"

        result_lines.append(function_signature)
        result_lines.extend(sliced_body_lines)
        result_lines.append("}")

        return "\n".join(result_lines)

    def _save_slice_results(self, original_code: str, sliced_code: str,
                           function_name: str, variable: str) -> None:
        """
        保存切片结果到文件
        Args:
            original_code: 原始函数代码
            sliced_code: 切片后的代码
            function_name: 函数名
            variable: 变量名
        """
        # 创建结果目录
        results_dir = "slice_results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{function_name}_{variable}_{timestamp}"

        # 保存原始函数代码
        original_file = os.path.join(results_dir, f"{base_filename}_original.c")
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write("// Original Function Code\n")
            f.write(f"// Function: {function_name}\n")
            f.write(f"// Variable: {variable}\n")
            f.write(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(original_code)

        # 保存切片后的代码
        sliced_file = os.path.join(results_dir, f"{base_filename}_sliced.c")
        with open(sliced_file, 'w', encoding='utf-8') as f:
            f.write("// Sliced Function Code\n")
            f.write(f"// Function: {function_name}\n")
            f.write(f"// Variable: {variable}\n")
            f.write(f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(sliced_code)

        # 保存比对报告
        report_file = os.path.join(results_dir, f"{base_filename}_report.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# Function Slice Report\n\n")
            f.write(f"**Function:** `{function_name}`  \n")
            f.write(f"**Variable:** `{variable}`  \n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")

            f.write("## Original Function\n\n")
            f.write("```c\n")
            f.write(original_code)
            f.write("\n```\n\n")

            f.write("## Sliced Function\n\n")
            f.write("```c\n")
            f.write(sliced_code)
            f.write("\n```\n\n")

            # 统计信息
            original_lines = len(original_code.splitlines())
            sliced_lines = len(sliced_code.splitlines())
            f.write("## Statistics\n\n")
            f.write(f"- Original lines: {original_lines}\n")
            f.write(f"- Sliced lines: {sliced_lines}\n")
            f.write(f"- Reduction: {original_lines - sliced_lines} lines ({((original_lines - sliced_lines) / original_lines * 100):.1f}%)\n")

        print(f"✅ 切片结果已保存:")
        print(f"   📄 原始代码: {original_file}")
        print(f"   ✂️  切片代码: {sliced_file}")
        print(f"   📊 比对报告: {report_file}")


def slice_function_by_variable(function_code: str, variable: str, language: str = "c",
                              function_name: str = None, save_to_file: bool = False) -> str:
    """
    对函数体进行变量相关切片（便捷函数）
    Args:
        function_code: 函数体源码字符串
        variable: 变量名
        language: "c" 或 "cpp"
        function_name: 函数名（用于保存文件）
        save_to_file: 是否保存到文件
    Returns:
        与变量相关的代码片段字符串（包含函数签名和大括号）
    """
    slicer = FunctionLevelSlicer(language)
    return slicer.slice_function_by_variable(function_code, variable, function_name, save_to_file)