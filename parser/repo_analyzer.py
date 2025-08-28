#!/usr/bin/env python3
"""
仓库分析器 - 基于用户配置文件的C/C++代码分析工具（核心分析逻辑）
"""

import time
import logging
import os
from typing import List, Dict, Optional
from .file_finder import FileFinder
from .function_extractor import FunctionExtractor
from .function_info import FunctionInfo
from .type_registry import TypeRegistry
from .type_extractor import TypeExtractor
from .config_parser import ConfigParser
from .call_graph import CallGraph
from .header_analyzer import HeaderAnalyzer
from .file_extensions import is_supported_file, is_cpp_file
from .function_usage_finder import FunctionUsageFinder

# logging
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
        self.is_single_file_mode = is_supported_file(config_or_file_path)
        self.input_file_path = config_or_file_path
        
        if self.is_single_file_mode:
            # 单文件模式：直接设置文件信息
            self.single_file_path = os.path.abspath(config_or_file_path)
            self.analysis_target_path = self.single_file_path  # 记录被分析的目标路径
            self.config_parser = None
        else:
            # 配置文件模式：解析配置文件
            self.config_parser = ConfigParser(config_or_file_path)
            self.analysis_target_path = self.config_parser.get_library_path()  # 记录被分析的目标路径
    
    def analyze(self) -> dict:
        """
        Conduct code analysis
        
        Returns:
            Analysis results dictionary
        """
        start_time = time.time()
        
        logger.info("Repo Analyzer Start ......")
        if self.is_single_file_mode:
            logger.info("Single File Mode")
        else:
            logger.info("Config File Mode")
        
        # Collect Files
        logger.info("Repo Analyzer Collect Files ......")
        
        files, error_msg = self._collect_files()
        if error_msg:
            error_msg = f"Repo Analyzer Collect Files Error: {error_msg}"
            logger.error(error_msg)
            return {'error': error_msg}
        
        if not files:
            error_msg = "❌ No C/C++ Files Found"
            logger.error(error_msg)
            return {'error': error_msg}
        
        # Display File Statistics
        logger.info(f"Repo Analyzer Find {len(files)} Files")
        
        # Extract Types
        logger.info("Repo Analyzer Extract Types ......")
        
        self._extract_types(files)
        
        # Extract Functions
        logger.info("Repo Analyzer Extract Functions ......")
        
        self.all_functions = self._extract_functions(files)
        
        processing_time = time.time() - start_time
        
        # Generate Statistics
        stats = self._calculate_stats(files, processing_time)
        
        logger.info("Repo Analyzer Finish ......")
        
        return stats
    
    def _collect_files(self) -> tuple[List[str], str]:
        """Collect files to be analyzed"""
        if self.is_single_file_mode:
            return [self.single_file_path], ""
        
        # Collect files from config
        all_files = []
        analysis_targets = self.config_parser.get_analysis_targets()
        
        for target_path in analysis_targets:
            if not os.path.exists(target_path):
                logger.warning(f"Target path does not exist: {target_path}")
                continue
            
            if os.path.isfile(target_path):
                # Single file
                if is_supported_file(target_path):
                    all_files.append(target_path)
            else:
                # Directory
                files = self.file_finder.find_files(target_path, recursive=True)
                all_files.extend(files)
        
        # Apply exclusions
        filtered_files = self._apply_exclusions(all_files)
        
        return filtered_files, ""
    
    def _extract_functions(self, files: List[str]) -> List[FunctionInfo]:
        """Extract function definitions"""
        all_functions = []
        failed_files = []
        
        for i, file_path in enumerate(files, 1):
            try:
                rel_path = self._get_relative_path(file_path)
                
                logger.debug(f"Processing file {i}/{len(files)}: {rel_path}")
                
                functions = self.function_extractor.extract_from_file(file_path)
                all_functions.extend(functions)
                
            except Exception as e:
                failed_files.append((file_path, str(e)))
                logger.error(f"Processing file {file_path} failed: {e}")
        
        # Build Call Graph
        logger.info("Building Call Graph...")
        
        # Add all functions to Call Graph
        for func in all_functions:
            self.call_graph.add_function(func)
        
        # Build call graph
        self.call_graph.build_graph()
        
        logger.info("Call Graph building completed")
        
        return all_functions
    
    def _apply_exclusions(self, files: List[str]) -> List[str]:
        """Apply exclusion rules to filter files"""
        if self.is_single_file_mode:
            # Single file mode: no exclusion rules
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
                    # Exclude specific file
                    if abs_file_path == exclude_path:
                        should_exclude = True
                        break
                else:
                    # Exclude all files in directory
                    if abs_file_path.startswith(exclude_path + os.sep) or abs_file_path == exclude_path:
                        should_exclude = True
                        break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _extract_types(self, files: List[str]) -> None:
        """Extract type definitions"""
        type_count = 0
        
        for i, file_path in enumerate(files, 1):
            try:
                rel_path = self._get_relative_path(file_path)
                
                logger.debug(f"Analyzing types {i}/{len(files)}: {rel_path}")
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if it's a C++ file
                is_cpp = is_cpp_file(file_path)
                
                # Parse code using tree_sitter_manager
                tree = self.function_extractor.tree_sitter_manager.parse_content(content, file_path)
                if tree is None:
                    logger.warning(f"Failed to parse {file_path}")
                    continue
                root_node = tree.root_node
                
                # Extract type definitions
                self.type_extractor.extract_from_content(content, root_node, file_path)
                
                # Extract types from preprocessor directives (e.g., #define type aliases)
                self.type_extractor.extract_from_preprocessor(content)
                
                logger.debug(f" -> OK")
                
            except Exception as e:
                logger.error(f"Type extraction failed {file_path}: {e}")
        
        # Get type statistics   
        type_stats = self.type_registry.get_statistics()
        type_count = type_stats.get('total_types', 0)
        
        logger.info(f"Type extraction completed, found {type_count} type definitions")
    
    def _get_type_summary_text(self) -> str:
        """Get type summary text"""
        stats = self.type_registry.get_statistics()
        
        return (f"📋 Type Statistics:\n"
                f"  • Total: {stats.get('total_types', 0)} types\n"
                f"  • typedef: {stats.get('typedef', 0)} types\n"
                f"  • struct: {stats.get('struct', 0)} types\n"
                f"  • union: {stats.get('union', 0)} types\n"
                f"  • enum: {stats.get('enum', 0)} types\n"
                f"  • pointer typedef: {stats.get('pointer_typedefs', 0)} types\n")
    
    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path display"""
        if self.is_single_file_mode:
            # Single file mode: return filename 
            return os.path.basename(file_path)
            
        try:
            # Try to calculate relative path relative to library path
            library_path = self.config_parser.get_library_path()
            return os.path.relpath(file_path, library_path)
        except ValueError:
            # If relative path cannot be calculated, return filename
            return os.path.basename(file_path)
    
    def _calculate_stats(self, files: List[str], duration: float) -> Dict:
        """Calculate analysis statistics"""
        total_functions = len(self.all_functions)
        definitions = len([f for f in self.all_functions if not f.is_declaration])
        declarations = len([f for f in self.all_functions if f.is_declaration])
        
        # Detect duplicate functions
        function_names = {}
        for func in self.all_functions:
            key = (func.name, func.is_declaration)
            if key not in function_names:
                function_names[key] = []
            function_names[key].append(func)
        
        duplicate_functions = {k: v for k, v in function_names.items() if len(v) > 1}
        
        # Get type statistics
        type_stats = self.type_registry.get_statistics()
        
        stats = {
            'total_files': len(files),
            'processed_files': len(files),
            'failed_files': 0,  
            'total_functions': total_functions,
            'function_definitions': definitions,
            'function_declarations': declarations,
            'duplicate_functions': len(duplicate_functions),
            'processing_time': duration,
            'files_per_second': len(files) / duration if duration > 0 else 0,
            'duplicate_function_details': duplicate_functions,
            'type_statistics': type_stats
        }
        
        return stats
    
    def search_functions(self, function_name: str, exact_match: bool = True, case_sensitive: bool = True) -> List[FunctionInfo]:
        """
        Search for functions with matching names
        
        Args:
            function_name: The name of the function to search for
            exact_match: Whether to perform an exact match (default: True)
            case_sensitive: Whether to be case sensitive (default: True)
            
        Returns:
            A list of FunctionInfo objects that match the search criteria
        """
        matches = []
        
        # Preprocess search condition
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
        Extract functions that contain the specified API keyword
        
        Args:
            api_keyword: API keyword (e.g., "CJSON_PUBLIC", "API", "EXPORT" etc.)
            include_declarations: Whether to include function declarations
            include_definitions: Whether to include function definitions
            
        Returns:
            A list of FunctionInfo objects that contain the API keyword
        """
        if not self.all_functions:
            logger.warning("No function analysis has been performed yet. Please call the analyze() method first.")
            return []
        
        api_functions = []
        
        for func in self.all_functions:
            # Filter function types based on user selection
            if func.is_declaration and not include_declarations:
                continue
            if not func.is_declaration and not include_definitions:
                continue
            
            # Use FunctionInfo method to check if it contains the API keyword
            if func.is_api_function(api_keyword):
                api_functions.append(func)
        
        return api_functions
    
    def get_functions(self) -> List[FunctionInfo]:
        """
        Get all functions found
        
        Returns:
            A list of FunctionInfo objects
        """
        return self.all_functions
    
    def get_function_complete_comments(self, function_name: str) -> str:
        """
        Get the complete comments of a function (including comments from declarations and definitions)
        
        Args:
            function_name: Function name
            
        Returns:
            Combined complete comment string
        """
        # Find all functions with the same name (declarations and definitions)
        matching_functions = self.search_functions(function_name, exact_match=True, case_sensitive=True)
        
        if not matching_functions:
            return ""
        
        all_comments = []
        seen_comments = set()  # Avoid duplicate comments
        
        # Prefer declarations because declarations usually have more detailed API documentation in header files
        declarations = [func for func in matching_functions if func.is_declaration]
        definitions = [func for func in matching_functions if not func.is_declaration]
        
        # First collect comments from declarations
        for func in declarations:
            comments = func.get_comments()
            if comments and comments not in seen_comments:
                all_comments.append({
                    'type': 'Declaration',
                    'file': func.file_path,
                    'line': func.start_line,
                    'content': comments
                })
                seen_comments.add(comments)
        
        # Then collect comments from definitions
        for func in definitions:
            comments = func.get_comments()
            if comments and comments not in seen_comments:
                all_comments.append({
                    'type': 'Definition',
                    'file': func.file_path,
                    'line': func.start_line,
                    'content': comments
                })
                seen_comments.add(comments)
        
        # Merge comments
        if not all_comments:
            return ""
        elif len(all_comments) == 1:
            return all_comments[0]['content']
        else:
            # When multiple comments exist, combine them
            combined_comments = []
            for comment_info in all_comments:
                file_name = os.path.basename(comment_info['file'])
                header = f"=== {comment_info['type']} ({file_name}:{comment_info['line']}) ==="
                combined_comments.append(header)
                combined_comments.append(comment_info['content'])
                combined_comments.append("")  # Add a blank line separator
            
            return '\n'.join(combined_comments).rstrip()
    
    def get_function_comment_summary(self, function_name: str) -> dict:
        """
        Get detailed summary information of function comments
        
        Args:
            function_name: Function name
            
        Returns:
            A dictionary containing comment statistics and source information
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
                    'type': 'Declaration' if func.is_declaration else 'Definition',
                    'file': func.file_path,
                    'line': func.start_line,
                    'has_comments': func.has_comments(),
                    'comment_length': len(func.get_comments()) if func.has_comments() else 0
                }
                for func in matching_functions
            ]
        }
    
    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.analysis_stats
    
    def get_processed_files(self) -> List[str]:
        """Get the list of processed files"""
        return self.processed_files
    
    def get_function_by_name(self, function_name: str, exact_match: bool = True) -> List[FunctionInfo]:
        """
        Get function information by name
        
        Args:
            function_name: Function name to search for
            exact_match: Whether to perform exact matching, False for fuzzy matching
            
        Returns:
            List of matching function information
        """
        # Use search_functions to avoid code duplication
        return self.search_functions(function_name, exact_match=exact_match, case_sensitive=False)
    
    def get_function_body(self, function_name: str, exact_match: bool = True) -> Dict[str, str]:
        """
        Get function body content by name
        
        Args:
            function_name: Function name to search for
            exact_match: Whether to perform exact matching
            
        Returns:
            Dictionary, key is the unique identifier of the function, value is the function body content
        """
        matches = self.get_function_by_name(function_name, exact_match)
        result = {}
        
        for func in matches:
            # Create a unique identifier: function_name_filename_line_number
            file_name = os.path.basename(func.file_path)
            key = f"{func.name}_{file_name}_{func.start_line}"
            
            body = func.get_body()
            if body is not None:
                result[key] = body
        
        return result
    
    def get_type_registry(self) -> TypeRegistry:
        """Get the type registry"""
        return self.type_registry
    
    def lookup_type(self, type_name: str) -> Optional[Dict]:
        """Get type information by name"""
        type_info = self.type_registry.lookup_type(type_name)
        return type_info.to_dict() if type_info else None
    
    def get_type_statistics(self) -> Dict:
        """Get type statistics"""
        return self.type_registry.get_statistics()
    
    def get_config_summary_text(self) -> str:
        """Get configuration summary text"""
        return self._get_config_summary_text()
    
    def _get_config_summary_text(self) -> str:
        """Get configuration summary text (internal method)"""
        if self.is_single_file_mode:
            return (f"📋 Single file analysis mode:\n"
                    f"   File path: {self.single_file_path}\n"
                    f"   File name: {os.path.basename(self.single_file_path)}\n"
                    f"   ➤ Analyze a single C/C++ file")
        else:
            return self.config_parser.get_config_summary_text()
      
    def export_all_types(self) -> Dict:
        """Export all type information"""
        return self.type_registry.export_types()
    
    # ===== Call Graph =====
    
    def get_call_graph(self) -> CallGraph:
        """Get the call graph instance"""
        return self.call_graph  
    
    def get_function_dependencies(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        Get all dependencies of a function
        
        Args:
            func_name: Function name
            max_depth: Maximum recursive depth
            
        Returns:
            Mapping of dependent function names to depths
        """
        return self.call_graph.get_all_dependencies(func_name, max_depth)
    
    def get_function_dependents(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        Get all functions that depend on this function
        
        Args:
            func_name: Function name
            max_depth: Maximum recursive depth
            
        Returns:
            Mapping of dependent function names to depths
        """
        return self.call_graph.get_all_dependents(func_name, max_depth)
    
    def get_direct_callees(self, func_name: str) -> set:
        """Get the functions directly called by this function"""
        return self.call_graph.get_direct_callees(func_name)
    
    def get_direct_callers(self, func_name: str) -> set:
        """Get the functions that directly call this function"""
        return self.call_graph.get_direct_callers(func_name)
    
    def find_call_chains(self, from_func: str, to_func: str, max_depth: int = 10) -> List[List[str]]:
        """Find call chains from one function to another"""
        return self.call_graph.get_call_chain(from_func, to_func, max_depth)
    
    def find_cycles(self) -> List[List[str]]:
        """Find circular dependencies"""
        return self.call_graph.find_cycles()
    
    def get_external_dependencies(self) -> set:
        """Get external dependencies (functions not in the current analysis scope)"""
        return self.call_graph.get_external_dependencies()
    
    def get_call_graph_summary(self) -> Dict:
        """Get Call Graph summary information"""
        return self.call_graph.get_graph_summary()
    
    def get_function_complexity_stats(self) -> Dict[str, Dict]:
        """Get function complexity statistics"""
        return self.call_graph.get_function_complexity_stats()
    
    def analyze_headers(self, target_files: List[str] = None) -> dict:
        """
        Analyze the include relationships of header files
        
        Args:
            target_files: List of header files to analyze (optional)
            show_progress: Whether to display progress
            
        Returns:
            Header file analysis results
        """
        analyzer = HeaderAnalyzer()
        
        if self.is_single_file_mode:
            # single file mode
            return analyzer.analyze_from_single_file_mode(self.single_file_path)
        else:
            # repo mode
            return analyzer.analyze_from_repo(self.config_parser, target_files)
    
    def search_includes(self, header_results: dict, pattern: str) -> List[dict]:
        """Search for include relationships in header file analysis results"""
        analyzer = HeaderAnalyzer()
        return analyzer.search_includes(header_results, pattern)
    
    def get_include_dependency_graph(self, header_results: dict) -> Dict[str, List[str]]:
        """Get the include dependency graph"""
        analyzer = HeaderAnalyzer()
        return analyzer.get_dependency_graph(header_results)
    
    def get_function_callers(self, function_name: str) -> List[str]:
        """
        Get all direct callers of the specified function
        
        Args:
            function_name: Name of the function to find callers for
            
        Returns:
            List of direct caller function names. If the function does not exist or the call graph has not been built, returns an empty list.
        """
        if not self.call_graph._graph_built:
            return []
        
        if function_name not in self.call_graph.functions:
            return []
        
        # Get direct callers and sort them
        direct_callers = self.get_direct_callers(function_name)
        return sorted(list(direct_callers))
    
    def get_analysis_target_path(self) -> str:
        """
        Get the target path being analyzed
        
        Returns:
            Single file mode: returns the absolute path of the file
            Config file mode: returns the library root directory path
        """
        return self.analysis_target_path
    
    def get_analysis_mode(self) -> str:
        """
        Get the current analysis mode
        
        Returns:
            "single_file" or "config_file"
        """
        return "single_file" if self.is_single_file_mode else "config_file"
    
    def _get_usage_finder_and_repo_root(self, repo_root: str = None) -> tuple:
        """
        获取FunctionUsageFinder实例和repo_root路径的辅助方法
        
        Args:
            repo_root: 仓库根目录，如果为None则使用分析目标路径
        
        Returns:
            tuple: (usage_finder, repo_root)
        """
        
        # 处理repo_root
        if repo_root is None:
            if self.is_single_file_mode:
                repo_root = os.path.dirname(self.analysis_target_path)
            else:
                repo_root = self.analysis_target_path
        
        # 创建FunctionUsageFinder实例（支持config_parser为None的情况）
        usage_finder = FunctionUsageFinder(self.config_parser)
        
        return usage_finder, repo_root
    
    def find_usage_in_include_files(self, function_name: str) -> Dict[str, List[str]]:
        """
        在include_files中查找函数使用
        
        Args:
            function_name: 要查找的函数名
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        # 单文件模式下没有config_parser，返回空结果
        if self.config_parser is None:
            return {}
        
        usage_finder, _ = self._get_usage_finder_and_repo_root()
        return usage_finder.find_usage_in_include_files(
            function_name=function_name,
            analyzed_functions=self.all_functions
        )
    
    def find_usage_in_non_include_files(self, function_name: str) -> Dict[str, List[str]]:
        """
        在非include_files中查找函数使用
        
        Args:
            function_name: 要查找的函数名
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        usage_finder, repo_root = self._get_usage_finder_and_repo_root()
        return usage_finder.find_usage_in_non_include_files(
            function_name=function_name,
            repo_root=repo_root
        )
    
    def find_usage_in_all_files(self, function_name: str) -> Dict[str, List[str]]:
        """
        在所有文件中查找函数使用
        
        Args:
            function_name: 要查找的函数名
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        usage_finder, repo_root = self._get_usage_finder_and_repo_root()
        return usage_finder.find_usage_in_all_files(
            function_name=function_name,
            repo_root=repo_root,
            analyzed_functions=self.all_functions
        )
    
    def find_usage_in_test_files(self, function_name: str) -> Dict[str, List[str]]:
        """
        在test文件中查找函数使用
        
        Args:
            function_name: 要查找的函数名
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        usage_finder, repo_root = self._get_usage_finder_and_repo_root()
        return usage_finder.find_usage_in_test_files(
            function_name=function_name,
            repo_root=repo_root
        )