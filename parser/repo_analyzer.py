#!/usr/bin/env python3
"""
仓库分析器 - 基于用户配置文件的C/C++代码分析工具（核心分析逻辑）
"""

import time
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from .file_finder import FileFinder
from .function_extractor import FunctionExtractor
from .function_info import FunctionInfo
from .type_registry import TypeRegistry
from .type_extractor import TypeExtractor
from .config_parser import ConfigParser
from .call_graph import CallGraph
from .header_analyzer import HeaderAnalyzer

# 配置logging
logger = logging.getLogger(__name__)

class RepoAnalyzer:
    """代码仓库分析器（核心分析功能）"""
    
    def __init__(self, config_or_file_path: str):
        """
        初始化分析器
        
        Args:
            config_or_file_path: 配置文件路径或C/C++文件路径
        """
        self.file_finder = FileFinder()
        
        # 初始化类型注册表和相关组件
        self.type_registry = TypeRegistry()
        self.type_extractor = TypeExtractor(self.type_registry)
        self.function_extractor = FunctionExtractor(self.type_registry)
        
        # 初始化Call Graph
        self.call_graph = CallGraph()
        
        self.all_functions = []
        self.analysis_stats = {}
        self.processed_files = []
        
        # 智能识别输入类型
        self.is_single_file_mode = self._is_cpp_file(config_or_file_path)
        self.input_file_path = config_or_file_path
        
        if self.is_single_file_mode:
            # 单文件模式：直接设置文件信息
            self.single_file_path = os.path.abspath(config_or_file_path)
            self.config_parser = None
        else:
            # 配置文件模式：解析配置文件
            self.config_parser = ConfigParser(config_or_file_path)
    
    def _is_cpp_file(self, file_path: str) -> bool:
        """检查是否为C/C++文件"""
        if not os.path.exists(file_path):
            return False
        
        if not os.path.isfile(file_path):
            return False
        
        # 检查文件扩展名
        supported_extensions = {'.c', '.h', '.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'}
        file_ext = Path(file_path).suffix.lower()
        return file_ext in supported_extensions
    
    def analyze(self) -> dict:
        """
        执行代码分析
        
        Args:
        
        Returns:
            分析结果字典
        """
        start_time = time.time()
        
        logger.info("开始代码分析")
        if self.is_single_file_mode:
            logger.info("单文件模式分析")
        else:
            logger.info("基于配置文件的代码分析")
        
        # 收集文件
        logger.info("正在收集C/C++文件...")
        
        files, error_msg = self._collect_files()
        if error_msg:
            error_msg = f"错误: {error_msg}"
            logger.error(error_msg)
            return {'error': error_msg}
        
        if not files:
            error_msg = "❌ 未找到任何C/C++文件"
            logger.error(error_msg)
            return {'error': error_msg}
        
        # 显示文件统计
        file_stats = self._get_file_statistics(files)
        logger.info(f"找到 {file_stats['total_files']} 个文件")
        
        # 提取类型定义
        logger.info("正在提取类型定义...")
        
        self._extract_types(files)
        
        # 提取函数
        logger.info("正在提取函数定义...")
        
        self.all_functions = self._extract_functions(files)
        
        processing_time = time.time() - start_time
        
        # 计算统计信息
        stats = self._calculate_stats(files, processing_time)
        
        logger.info("分析完成！")
        
        return stats
    
    def _collect_files(self) -> tuple[List[str], str]:
        """收集需要分析的文件"""
        if self.is_single_file_mode:
            # 单文件模式：直接返回单个文件
            return [self.single_file_path], ""
        
        # 配置文件模式：原有逻辑
        all_files = []
        analysis_targets = self.config_parser.get_analysis_targets()
        
        for target_path in analysis_targets:
            if not os.path.exists(target_path):
                logger.warning(f"目标路径不存在: {target_path}")
                continue
            
            if os.path.isfile(target_path):
                # 单个文件
                if self._is_supported_file(target_path):
                    all_files.append(target_path)
            else:
                # 目录
                files = self.file_finder.find_files(target_path, recursive=True)
                all_files.extend(files)
        
        # 应用排除规则
        filtered_files = self._apply_exclusions(all_files)
        
        return filtered_files, ""
    
    def _extract_functions(self, files: List[str]) -> List[FunctionInfo]:
        """提取函数定义"""
        all_functions = []
        failed_files = []
        
        for i, file_path in enumerate(files, 1):
            try:
                rel_path = self._get_relative_path(file_path)
                
                logger.debug(f"处理文件 {i}/{len(files)}: {rel_path}")
                
                functions = self.function_extractor.extract_from_file(file_path)
                all_functions.extend(functions)
                
            except Exception as e:
                failed_files.append((file_path, str(e)))
                logger.error(f"处理文件 {file_path} 失败: {e}")
        
        # 构建Call Graph
        logger.info("正在构建Call Graph...")
        
        # 将所有函数添加到Call Graph
        for func in all_functions:
            self.call_graph.add_function(func)
        
        # 构建调用关系图
        self.call_graph.build_graph()
        
        logger.info("Call Graph构建完成")
        
        return all_functions
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查是否为支持的C/C++文件"""
        return self.file_finder._is_c_cpp_file(Path(file_path))
    
    def _apply_exclusions(self, files: List[str]) -> List[str]:
        """应用排除规则过滤文件"""
        if self.is_single_file_mode:
            # 单文件模式：无排除规则
            return files
            
        exclude_targets = self.config_parser.get_exclude_targets()
        if not exclude_targets:
            return files
        
        filtered_files = []
        exclude_paths_abs = [os.path.abspath(path) for path in exclude_targets]
        
        for file_path in files:
            abs_file_path = os.path.abspath(file_path)
            should_exclude = False
            
            for exclude_path in exclude_paths_abs:
                if os.path.isfile(exclude_path):
                    # 排除特定文件
                    if abs_file_path == exclude_path:
                        should_exclude = True
                        break
                else:
                    # 排除目录下的所有文件
                    if abs_file_path.startswith(exclude_path + os.sep) or abs_file_path == exclude_path:
                        should_exclude = True
                        break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _extract_types(self, files: List[str]) -> None:
        """提取类型定义"""
        type_count = 0
        
        for i, file_path in enumerate(files, 1):
            try:
                rel_path = self._get_relative_path(file_path)
                
                logger.debug(f"分析类型 {i}/{len(files)}: {rel_path}")
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 判断是否为C++文件
                is_cpp = any(file_path.endswith(ext) for ext in ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'])
                
                # 选择合适的解析器
                parser = self.function_extractor.cpp_parser if is_cpp else self.function_extractor.c_parser
                
                # 解析代码
                tree = parser.parse(content.encode('utf-8'))
                root_node = tree.root_node
                
                # 提取类型定义
                self.type_extractor.extract_from_content(content, root_node, file_path)
                
                # 从预处理器指令中提取类型（如#define的类型别名）
                self.type_extractor.extract_from_preprocessor(content)
                
                logger.debug(f" -> OK")
                
            except Exception as e:
                logger.error(f"提取类型定义失败 {file_path}: {e}")
        
        # 获取类型统计
        type_stats = self.type_registry.get_statistics()
        type_count = type_stats.get('total_types', 0)
        
        logger.info(f"类型提取完成，找到 {type_count} 个类型定义")
    
    def _get_type_summary_text(self) -> str:
        """获取类型摘要文本"""
        stats = self.type_registry.get_statistics()
        
        return (f"📋 类型统计:\n"
                f"  • 总计: {stats.get('total_types', 0)} 个类型\n"
                f"  • typedef: {stats.get('typedef', 0)} 个\n"
                f"  • 结构体: {stats.get('struct', 0)} 个\n"
                f"  • 联合体: {stats.get('union', 0)} 个\n"
                f"  • 枚举: {stats.get('enum', 0)} 个\n"
                f"  • 指针typedef: {stats.get('pointer_typedefs', 0)} 个")
    
    def _get_relative_path(self, file_path: str) -> str:
        """获取相对路径显示"""
        if self.is_single_file_mode:
            # 单文件模式：返回文件名
            return os.path.basename(file_path)
            
        try:
            # 尝试相对于库路径
            library_path = self.config_parser.get_library_path()
            return os.path.relpath(file_path, library_path)
        except ValueError:
            # 如果无法计算相对路径，返回文件名
            return os.path.basename(file_path)
    
    def _calculate_stats(self, files: List[str], duration: float) -> Dict:
        """生成分析统计信息"""
        total_functions = len(self.all_functions)
        definitions = len([f for f in self.all_functions if not f.is_declaration])
        declarations = len([f for f in self.all_functions if f.is_declaration])
        
        # 检测重复函数
        function_names = {}
        for func in self.all_functions:
            key = (func.name, func.is_declaration)
            if key not in function_names:
                function_names[key] = []
            function_names[key].append(func)
        
        duplicate_functions = {k: v for k, v in function_names.items() if len(v) > 1}
        
        # 获取类型统计
        type_stats = self.type_registry.get_statistics()
        
        stats = {
            'total_files': len(files),
            'processed_files': len(files),
            'failed_files': 0,  # 暂时简化，不追踪失败文件
            'total_functions': total_functions,
            'function_definitions': definitions,
            'function_declarations': declarations,
            'duplicate_functions': len(duplicate_functions),
            'processing_time': duration,
            'files_per_second': len(files) / duration if duration > 0 else 0,
            'duplicate_function_details': duplicate_functions,
            # 新增：类型统计信息
            'type_statistics': type_stats
        }
        
        return stats
    
    def search_functions(self, function_name: str, exact_match: bool = True, case_sensitive: bool = True) -> List[FunctionInfo]:
        """
        搜索函数名匹配的函数
        
        Args:
            function_name: 要搜索的函数名
            exact_match: 是否精确匹配，False时进行包含匹配
            case_sensitive: 是否大小写敏感
            
        Returns:
            匹配的函数列表
        """
        matches = []
        
        # 预处理搜索条件
        search_name = function_name if case_sensitive else function_name.lower()
        
        for func in self.all_functions:
            func_name = func.name if case_sensitive else func.name.lower()
            
            if exact_match:
                if func_name == search_name:
                    matches.append(func)
            else:
                if search_name in func_name:
                    matches.append(func)
        
        return matches
    
    def get_api_functions(self, api_keyword: str, include_declarations: bool = True, 
                         include_definitions: bool = True) -> List[FunctionInfo]:
        """
        根据关键字提取API函数
        
        Args:
            api_keyword: API关键字（如 "CJSON_PUBLIC", "API", "EXPORT" 等）
            include_declarations: 是否包含函数声明
            include_definitions: 是否包含函数定义
            
        Returns:
            包含API关键字的函数列表
        """
        if not self.all_functions:
            logger.warning("尚未进行函数分析，请先调用analyze()方法")
            return []
        
        api_functions = []
        
        for func in self.all_functions:
            # 根据用户选择过滤函数类型
            if func.is_declaration and not include_declarations:
                continue
            if not func.is_declaration and not include_definitions:
                continue
            
            # 使用FunctionInfo的方法检查是否包含API关键字
            if func.is_api_function(api_keyword):
                api_functions.append(func)
        
        return api_functions
    
    def get_functions(self) -> List[FunctionInfo]:
        """获取所有找到的函数"""
        return self.all_functions
    
    def get_function_complete_comments(self, function_name: str) -> str:
        """
        获取函数的完整注释（包括声明和定义的注释）
        
        Args:
            function_name: 函数名
            
        Returns:
            合并后的完整注释字符串
        """
        # 找到所有同名函数（声明和定义）
        matching_functions = self.search_functions(function_name, exact_match=True, case_sensitive=True)
        
        if not matching_functions:
            return ""
        
        all_comments = []
        seen_comments = set()  # 避免重复注释
        
        # 优先处理声明，因为声明通常在头文件中有更详细的API文档
        declarations = [func for func in matching_functions if func.is_declaration]
        definitions = [func for func in matching_functions if not func.is_declaration]
        
        # 首先收集声明的注释
        for func in declarations:
            comments = func.get_comments()
            if comments and comments not in seen_comments:
                all_comments.append({
                    'type': '声明',
                    'file': func.file_path,
                    'line': func.start_line,
                    'content': comments
                })
                seen_comments.add(comments)
        
        # 然后收集定义的注释
        for func in definitions:
            comments = func.get_comments()
            if comments and comments not in seen_comments:
                all_comments.append({
                    'type': '定义',
                    'file': func.file_path,
                    'line': func.start_line,
                    'content': comments
                })
                seen_comments.add(comments)
        
        # 合并注释
        if not all_comments:
            return ""
        elif len(all_comments) == 1:
            return all_comments[0]['content']
        else:
            # 多个注释时，组合显示
            combined_comments = []
            for comment_info in all_comments:
                file_name = os.path.basename(comment_info['file'])
                header = f"=== {comment_info['type']} ({file_name}:{comment_info['line']}) ==="
                combined_comments.append(header)
                combined_comments.append(comment_info['content'])
                combined_comments.append("")  # 空行分隔
            
            return '\n'.join(combined_comments).rstrip()
    
    def get_function_comment_summary(self, function_name: str) -> dict:
        """
        获取函数注释的详细摘要信息
        
        Args:
            function_name: 函数名
            
        Returns:
            包含注释统计和源信息的字典
        """
        matching_functions = self.search_functions(function_name, exact_match=True, case_sensitive=True)
        
        if not matching_functions:
            return {
                'function_exists': False,
                'total_instances': 0,
                'declarations_with_comments': 0,
                'definitions_with_comments': 0,
                'total_comment_length': 0,
                'has_any_comments': False
            }
        
        declarations = [func for func in matching_functions if func.is_declaration]
        definitions = [func for func in matching_functions if not func.is_declaration]
        
        declarations_with_comments = [func for func in declarations if func.has_comments()]
        definitions_with_comments = [func for func in definitions if func.has_comments()]
        
        complete_comments = self.get_function_complete_comments(function_name)
        
        return {
            'function_exists': True,
            'total_instances': len(matching_functions),
            'declarations': len(declarations),
            'definitions': len(definitions),
            'declarations_with_comments': len(declarations_with_comments),
            'definitions_with_comments': len(definitions_with_comments),
            'total_comment_length': len(complete_comments),
            'has_any_comments': bool(complete_comments),
            'complete_comments': complete_comments,
            'comment_sources': [
                {
                    'type': '声明' if func.is_declaration else '定义',
                    'file': func.file_path,
                    'line': func.start_line,
                    'has_comments': func.has_comments(),
                    'comment_length': len(func.get_comments()) if func.has_comments() else 0
                }
                for func in matching_functions
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return self.analysis_stats
    
    def get_processed_files(self) -> List[str]:
        """获取已处理的文件列表"""
        return self.processed_files
    
    def get_function_by_name(self, function_name: str, exact_match: bool = True) -> List[FunctionInfo]:
        """
        根据函数名获取函数信息
        
        Args:
            function_name: 要查找的函数名
            exact_match: 是否精确匹配，False时进行模糊匹配
            
        Returns:
            匹配的函数信息列表
        """
        # 使用 search_functions 来避免代码重复
        return self.search_functions(function_name, exact_match=exact_match, case_sensitive=False)
    
    def get_function_body(self, function_name: str, exact_match: bool = True) -> Dict[str, str]:
        """
        根据函数名获取函数体内容
        
        Args:
            function_name: 要查找的函数名
            exact_match: 是否精确匹配
            
        Returns:
            字典，键为函数的唯一标识，值为函数体内容
        """
        matches = self.get_function_by_name(function_name, exact_match)
        result = {}
        
        for func in matches:
            # 创建唯一标识：函数名_文件名_行号
            file_name = os.path.basename(func.file_path)
            key = f"{func.name}_{file_name}_{func.start_line}"
            
            body = func.get_body()
            if body is not None:
                result[key] = body
        
        return result
    
    def get_type_registry(self) -> TypeRegistry:
        """获取类型注册表"""
        return self.type_registry
    
    def lookup_type(self, type_name: str) -> Optional[Dict]:
        """查找类型信息"""
        type_info = self.type_registry.lookup_type(type_name)
        return type_info.to_dict() if type_info else None
    
    def get_type_statistics(self) -> Dict:
        """获取类型统计信息"""
        return self.type_registry.get_statistics()
    
    def get_config_summary_text(self) -> str:
        """获取配置摘要文本"""
        return self._get_config_summary_text()
    
    def _get_config_summary_text(self) -> str:
        """获取配置摘要文本（内部方法）"""
        if self.is_single_file_mode:
            return (f"📋 单文件分析模式:\n"
                    f"   文件路径: {self.single_file_path}\n"
                    f"   文件名: {os.path.basename(self.single_file_path)}\n"
                    f"   ➤ 分析单个C/C++文件")
        else:
            return self.config_parser.get_config_summary_text()
    
    def _get_file_statistics(self, files: List[str]) -> dict:
        """获取文件统计信息"""
        total_files = len(files)
        c_files = sum(1 for f in files if f.endswith(('.c',)))
        cpp_files = sum(1 for f in files if f.endswith(('.cpp', '.cxx', '.cc')))
        header_files = sum(1 for f in files if f.endswith(('.h', '.hpp', '.hxx', '.hh')))
        
        return {
            'total_files': total_files,
            'c_files': c_files,
            'cpp_files': cpp_files,
            'header_files': header_files
        }
    
    def _format_file_stats(self, file_stats: dict) -> str:
        """格式化文件统计信息"""
        return (f"✅ 找到 {file_stats['total_files']} 个文件\n"
                f"   - C文件: {file_stats['c_files']}\n"
                f"   - C++文件: {file_stats['cpp_files']}\n"
                f"   - 头文件: {file_stats['header_files']}")
    
    def export_all_types(self) -> Dict:
        """导出所有类型信息"""
        return self.type_registry.export_types()
    
    # ===== Call Graph 相关方法 =====
    
    def get_call_graph(self) -> CallGraph:
        """获取Call Graph实例"""
        return self.call_graph
    
    def get_function_dependencies(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        获取函数的所有依赖
        
        Args:
            func_name: 函数名
            max_depth: 最大递归深度
            
        Returns:
            依赖函数名到深度的映射
        """
        return self.call_graph.get_all_dependencies(func_name, max_depth)
    
    def get_function_dependents(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        获取依赖该函数的所有函数
        
        Args:
            func_name: 函数名
            max_depth: 最大递归深度
            
        Returns:
            依赖该函数的函数名到深度的映射
        """
        return self.call_graph.get_all_dependents(func_name, max_depth)
    
    def get_direct_callees(self, func_name: str) -> set:
        """获取函数直接调用的函数"""
        return self.call_graph.get_direct_callees(func_name)
    
    def get_direct_callers(self, func_name: str) -> set:
        """获取直接调用该函数的函数"""
        return self.call_graph.get_direct_callers(func_name)
    
    def find_call_chains(self, from_func: str, to_func: str, max_depth: int = 10) -> List[List[str]]:
        """查找从一个函数到另一个函数的调用链"""
        return self.call_graph.get_call_chain(from_func, to_func, max_depth)
    
    def find_cycles(self) -> List[List[str]]:
        """查找循环依赖"""
        return self.call_graph.find_cycles()
    
    def get_external_dependencies(self) -> set:
        """获取外部依赖（不在当前分析范围内的函数）"""
        return self.call_graph.get_external_dependencies()
    
    def get_call_graph_summary(self) -> Dict:
        """获取Call Graph摘要信息"""
        return self.call_graph.get_graph_summary()
    
    def get_function_complexity_stats(self) -> Dict[str, Dict]:
        """获取函数复杂度统计"""
        return self.call_graph.get_function_complexity_stats()
    
    def analyze_headers(self, target_files: List[str] = None) -> dict:
        """
        分析头文件的include关系
        
        Args:
            target_files: 指定要分析的头文件列表（可选）
            show_progress: 是否显示进度
            
        Returns:
            头文件分析结果
        """
        analyzer = HeaderAnalyzer()
        
        if self.is_single_file_mode:
            # single file mode
            return analyzer.analyze_from_single_file_mode(self.single_file_path)
        else:
            # repo mode
            return analyzer.analyze_from_repo(self.config_parser, target_files)
    
    def search_includes(self, header_results: dict, pattern: str) -> List[dict]:
        """在头文件分析结果中搜索include"""
        analyzer = HeaderAnalyzer()
        return analyzer.search_includes(header_results, pattern)
    
    def get_include_dependency_graph(self, header_results: dict) -> Dict[str, List[str]]:
        """获取include依赖关系图"""
        analyzer = HeaderAnalyzer()
        return analyzer.get_dependency_graph(header_results)
    
    def get_function_callers(self, function_name: str) -> List[str]:
        """
        获取调用指定函数的所有直接调用者
        
        Args:
            function_name: 要查找调用者的函数名
            
        Returns:
            直接调用者函数名列表，如果函数不存在或未构建Call Graph则返回空列表
        """
        if not self.call_graph._graph_built:
            return []
        
        if function_name not in self.call_graph.functions:
            return []
        
        # 获取直接调用者并排序
        direct_callers = self.get_direct_callers(function_name)
        return sorted(list(direct_callers))