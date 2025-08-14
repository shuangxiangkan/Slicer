#!/usr/bin/env python3
"""
AST节点处理模块

提供AST节点的解析和处理功能
"""
from .utils import text

class Node:
    """程序分析节点"""
    
    def __init__(self, tree_sitter_node):
        """
        从tree-sitter节点创建分析节点
        Args:
            tree_sitter_node: tree-sitter解析的节点
        """
        # 初始化所有实例变量
        self.line = tree_sitter_node.start_point[0] + 1
        self.type = tree_sitter_node.type
        self.id = hash((tree_sitter_node.start_point, tree_sitter_node.end_point)) % 1000000
        self.is_branch = False
        self.text = ''  # 节点文本表示
        self.defs = set()  # 定义的变量集合
        self.uses = set()  # 使用的变量集合
        
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

        if tree_sitter_node.parent and tree_sitter_node.parent.type == 'do_statement' and tree_sitter_node.parent.child_by_field_name('condition') == tree_sitter_node:
            self.is_branch = True
        
        # 获取定义和使用信息
        # 对于分支语句，只分析条件部分，不包括语句体
        if tree_sitter_node.type in ['if_statement', 'while_statement', 'switch_statement']:
            self.defs, self.uses = self._get_branch_condition_def_use_info(tree_sitter_node)
        elif tree_sitter_node.type == 'for_statement':
            # for 循环需要特殊处理，因为它包含初始化、条件和更新三个部分
            self.defs, self.uses = self._get_for_statement_def_use_info(tree_sitter_node)
        else:
            self.defs, self.uses = self._get_def_use_info(tree_sitter_node)
    
    def _get_def_use_info(self, node):
        """获取节点的定义和使用信息"""
        defs = set()
        uses = set()
        
        # 对于函数定义节点，只分析函数签名部分，不包括函数体
        if node.type == 'function_definition':
            # 只分析函数参数部分
            identifiers = self._get_function_signature_identifiers(node)
        else:
            # 获取所有标识符
            identifiers = self._get_all_identifiers(node)
        
        # 分析定义和使用
        for identifier in identifiers:
            if self._is_definition(identifier, node):
                defs.add(text(identifier))
            else:
                uses.add(text(identifier))
        
        # 当前处理：函数调用中的参数既被视为定义也被视为使用（保守做法）
        # TODO: 做更精确的分析，区分参数是def还是use
        if node.type == 'call_expression':
            function_call_params = self._get_function_call_parameters(node)
            for param_var in function_call_params:
                defs.add(param_var)
                uses.add(param_var)
        
        return defs, uses
    
    def _get_branch_condition_def_use_info(self, branch_node):
        """获取分支语句条件部分的定义和使用信息"""
        defs = set()
        uses = set()
        
        # 根据分支类型提取条件部分
        condition_node = None
        
        if branch_node.type == 'if_statement':
            condition_node = branch_node.child_by_field_name('condition')
        elif branch_node.type in ['while_statement', 'for_statement']:
            condition_node = branch_node.child_by_field_name('condition')
        elif branch_node.type == 'switch_statement':
            condition_node = branch_node.child_by_field_name('value')
        
        # 如果找不到条件字段，回退到分析所有子节点直到语句体
        if not condition_node:
            if branch_node.type == 'if_statement':
                body = branch_node.child_by_field_name('consequence')
            else:
                body = branch_node.child_by_field_name('body')
            
            # 分析到语句体之前的所有子节点
            for child in branch_node.children:
                if child == body:
                    break
                identifiers = self._get_all_identifiers(child)
                for identifier in identifiers:
                    if self._is_definition(identifier, child):
                        defs.add(text(identifier))
                    else:
                        uses.add(text(identifier))
        else:
            # 只分析条件节点
            identifiers = self._get_all_identifiers(condition_node)
            for identifier in identifiers:
                if self._is_definition(identifier, condition_node):
                    defs.add(text(identifier))
                else:
                    uses.add(text(identifier))
        
        return defs, uses
    
    def _get_for_statement_def_use_info(self, for_node):
        """获取 for 循环语句的定义和使用信息"""
        defs = set()
        uses = set()
        
        # for 循环包含三个部分：初始化、条件、更新
        # 分析到语句体之前的所有子节点
        body = for_node.child_by_field_name('body')
        
        for child in for_node.children:
            if child == body:
                break
            # 分析每个子节点的标识符
            identifiers = self._get_all_identifiers(child)
            for identifier in identifiers:
                if self._is_definition(identifier, child):
                    defs.add(text(identifier))
                else:
                    uses.add(text(identifier))
        
        return defs, uses
    
    def _get_function_signature_identifiers(self, function_node):
        """获取函数签名中的标识符（只包括参数，不包括函数体）"""
        identifiers = []
        
        # 查找函数的参数列表
        for child in function_node.children:
            if child.type == 'function_declarator':
                # 查找参数列表
                for grandchild in child.children:
                    if grandchild.type == 'parameter_list':
                        self._collect_parameter_identifiers(grandchild, identifiers)
                        break
                break
        
        return identifiers
    
    def _collect_parameter_identifiers(self, param_list_node, identifiers):
        """收集参数列表中的标识符"""
        def collect_identifiers(n):
            if n is None:
                return
            if n.type == 'identifier':
                identifiers.append(n)
            for child in n.children:
                collect_identifiers(child)
        
        collect_identifiers(param_list_node)
    
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
        if parent.type == 'declaration':
            return True
        
        # 初始化声明器 - 只有被声明的变量是定义，初始化表达式中的变量是使用
        if parent.type == 'init_declarator':
            # 检查是否是声明的变量（通常是第一个子节点）
            declarator = parent.child_by_field_name('declarator')
            if declarator and self._contains_node(declarator, identifier_node):
                return True
            return False

        # 函数参数
        if parent.type == 'parameter_declaration':
            return True
        
        # 数组声明器中的标识符（如函数参数 int arr[]）
        if parent.type == 'array_declarator':
            # 检查是否在参数声明中
            grandparent = parent.parent
            if grandparent and grandparent.type == 'parameter_declaration':
                return True

        # 赋值表达式的左侧
        if parent.type == 'assignment_expression':
            left = parent.child_by_field_name('left')
            if left and self._contains_node(left, identifier_node):
                return True

        # 更新表达式 (++, --)
        if parent.type == 'update_expression':
            return True

        # 取地址操作符 (&variable) - 通常用于scanf等函数的输出参数
        if parent.type in ['unary_expression', 'pointer_expression']:
            operator = parent.children[0] if parent.children else None
            if operator and text(operator) == '&':
                # 检查是否在函数调用中作为参数
                grandparent = parent.parent
                if grandparent and grandparent.type == 'argument_list':
                    great_grandparent = grandparent.parent
                    if great_grandparent and great_grandparent.type == 'call_expression':
                        # 检查是否是scanf或类似的输入函数
                        function = great_grandparent.child_by_field_name('function')
                        if function:
                            func_name = text(function)
                            # scanf, fscanf, sscanf等都是向变量写入的函数
                            if func_name in ['scanf', 'fscanf', 'sscanf', 'gets', 'fgets']:
                                return True

        return False
    
    def _get_function_call_parameters(self, call_node):
        """获取函数调用中的参数变量（用于保守的def/use分析）"""
        param_vars = set()
        
        # 查找参数列表
        argument_list = call_node.child_by_field_name('arguments')
        if argument_list:
            for arg in argument_list.children:
                if arg.type != ',':
                    # 提取参数中的变量
                    arg_identifiers = self._get_all_identifiers(arg)
                    for identifier in arg_identifiers:
                        var_name = text(identifier)
                        # 排除字符串字面量和数字
                        if var_name and not var_name.startswith('"') and not var_name.isdigit():
                            param_vars.add(var_name)
        
        return param_vars
    
    def _contains_node(self, parent, target):
        """检查父节点是否包含目标节点"""
        if parent == target:
            return True
        for child in parent.children:
            if self._contains_node(child, target):
                return True
        return False