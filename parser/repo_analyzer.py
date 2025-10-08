#!/usr/bin/env python3
"""
仓库分析器 - 基于用户配置文件的C/C++代码分析工具（核心分析逻辑）
"""

import time
import logging
import os
import re
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
from .doc_api_searcher import DocumentApiSearcher

# logging
logger = logging.getLogger(__name__)

class RepoAnalyzer:
    """代码仓库分析器（核心分析功能）"""
    
    def __init__(self, config_or_file_path=None, library_path=None, header_files=None, include_files=None, exclude_files=None):
        """
        初始化分析器
        
        Args:
            config_or_file_path: 配置文件路径或C/C++文件路径
            library_path: 库的绝对路径（当使用直接参数模式时）
            header_files: 头文件的相对路径列表（相对于library_path）
            include_files: 包含文件的相对路径或文件夹列表（相对于library_path）
            exclude_files: 排除文件的相对路径或文件夹列表（相对于library_path）
        """
        # 参数验证
        direct_params_provided = any([library_path, header_files, include_files, exclude_files])
        
        if config_or_file_path is None and not direct_params_provided:
            raise ValueError("必须提供config_or_file_path或直接参数（library_path等）")
        if config_or_file_path is not None and direct_params_provided:
            raise ValueError("config_or_file_path和直接参数不能同时提供")
        if direct_params_provided and library_path is None:
            raise ValueError("使用直接参数模式时，library_path是必需的")
            
        self.file_finder = FileFinder()
        
        # 初始化类型注册表和相关组件
        self.type_registry = TypeRegistry()
        self.type_extractor = TypeExtractor(self.type_registry)
        self.function_extractor = FunctionExtractor(self.type_registry)
        
        # 初始化Call Graph
        self.call_graph = CallGraph()
        
        # 初始化文档API搜索器
        self.doc_api_searcher = DocumentApiSearcher()
        
        self.all_functions = []
        self.analysis_stats = {}
        self.processed_files = []
        
        # 根据输入类型进行初始化
        if direct_params_provided:
            # 直接参数模式
            self._init_from_params(library_path, header_files, include_files, exclude_files)
        elif is_supported_file(config_or_file_path):
            # 单文件模式
            self._init_single_file(config_or_file_path)
        else:
            # 配置文件模式
            self._init_from_config_file(config_or_file_path)
    
    def _init_from_params(self, library_path: str, header_files=None, include_files=None, exclude_files=None):
        """从直接参数初始化"""
        self.is_single_file_mode = False
        self.is_dict_config_mode = True  # 保持兼容性，使用字典配置模式的逻辑
        
        # 构建配置字典
        config_dict = {
            "library_path": library_path
        }
        
        if header_files is not None:
            config_dict["header_files"] = header_files if isinstance(header_files, list) else [header_files]
        
        if include_files is not None:
            config_dict["include_files"] = include_files if isinstance(include_files, list) else [include_files]
        
        if exclude_files is not None:
            config_dict["exclude_files"] = exclude_files if isinstance(exclude_files, list) else [exclude_files]
        
        self.config_dict = config_dict
        # 使用ConfigParser来处理字典配置
        self.config_parser = ConfigParser(config_dict)
        self.analysis_target_path = self.config_parser.get_library_path()
        self.input_file_path = None
    
    def _init_single_file(self, file_path: str):
        """单文件模式初始化"""
        self.is_single_file_mode = True
        self.is_dict_config_mode = False
        self.single_file_path = os.path.abspath(file_path)
        self.analysis_target_path = self.single_file_path
        self.config_parser = None
        self.config_dict = None
        self.input_file_path = file_path
    
    def _init_from_config_file(self, config_file_path: str):
        """配置文件模式初始化"""
        self.is_single_file_mode = False
        self.is_dict_config_mode = False
        self.config_parser = ConfigParser(config_file_path)
        self.analysis_target_path = self.config_parser.get_library_path()
        self.config_dict = None
        self.input_file_path = config_file_path
    
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
        
        all_files = []
        
        # 配置文件模式（包括字典配置，因为字典配置也通过ConfigParser处理）
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
    
    def get_api_functions(self, api_keyword, header_files: List[str] = None,
                         api_prefix = None) -> List[FunctionInfo]:
        """
        Get API function definitions based on keyword and prefix filtering.
        
        This method returns only function definitions (not declarations) that match the API criteria.
        It uses a text-based approach instead of tree-sitter's direct parsing to avoid parsing 
        issues with complex function declarations.
        
        Why not use tree-sitter directly?
        ================================
        Tree-sitter has known parsing issues with certain function declarations, particularly
        those with complex macro prefixes. For example, a declaration like:
        
            MOCKLIB_API mock_parser_t* mock_parser_create(void);
        
        May be incorrectly parsed by tree-sitter as two separate nodes:
        1. A 'declaration' node containing only "MOCKLIB_API mock_parser_t"
        2. An 'expression_statement' node containing "* mock_parser_create(void);"
        
        This fragmentation prevents the FunctionExtractor from correctly identifying
        the complete function declaration. The text-based approach used here:
        
        1. First extracts potential API function names from header files using regex
        2. Then matches these names against parsed function definitions
        3. Returns only the function definitions that match the API criteria
        
        This hybrid approach is more reliable and avoids tree-sitter's parsing limitations
        while still leveraging its capabilities for function body analysis.
        
        Args:
            api_keyword: API keyword (str) or list of keywords (e.g., "MOCKLIB_API", ["CJSON_PUBLIC", "TIFFAPI"])
            header_files: List of specific header files to search (if None, searches all header files)
            api_prefix: API function name prefix (str) or list of prefixes (e.g., "TIFF", ["cJSON", "json"]), if None then no prefix check
            
        Returns:
            A list of FunctionInfo objects containing only function definitions that match the API criteria
        """
        if not self.all_functions:
            logger.warning("No function analysis has been performed yet. Please call the analyze() method first.")
            return []
        
        # Convert single keyword/prefix to list for uniform processing
        keywords = [api_keyword] if isinstance(api_keyword, str) else api_keyword
        prefixes = [api_prefix] if isinstance(api_prefix, str) else (api_prefix if api_prefix else None)
        
        # Step 1: Extract potential API function names from header files using text matching
        api_function_names = self._extract_api_function_names_from_headers(keywords, prefixes, header_files)
        
        # Step 2: Find matching function definitions in our parsed function list
        api_functions = []
        seen_functions = set()  # To avoid duplicates
        
        for func in self.all_functions:
            # Only include function definitions, skip declarations
            if func.is_declaration:
                continue
            
            # Check if this function is in our API function names list
            if func.name in api_function_names:
                if func.name not in seen_functions:
                    api_functions.append(func)
                    seen_functions.add(func.name)
        
        return api_functions
    
    def _extract_api_function_names_from_headers(self, keywords: List[str], prefixes: List[str] = None, 
                                               header_files: List[str] = None) -> set:
        """
        Extract API function names from header files using text-based pattern matching.
        
        This method uses regular expressions to find function declarations with specific
        keywords (like CJSON_PUBLIC, etc.) and optional prefixes.
        
        This text-based approach is used instead of tree-sitter parsing because tree-sitter
        has known issues with parsing complex function declarations that include macro
        prefixes, often splitting them into multiple nodes incorrectly.
        
        Args:
            keywords: List of API keywords to search for
            prefixes: List of function name prefixes to filter by (optional)
            header_files: List of header files to search (if None, searches all header files)
            
        Returns:
            Set of function names that match the criteria
        """
        
        api_function_names = set()
        
        # Determine which files to search
        if header_files:
            # Check if all specified header files exist
            for file_path in header_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Header file not found: {file_path}")
            files_to_search = header_files
        else:
            # Search all header files in the project
            files_to_search = [f for f in self.processed_files if f.endswith(('.h', '.hpp', '.hxx'))]
        
        # Pattern to match function declarations/definitions
        # This pattern looks for: [keywords] [optional_space] [return_type] [*] function_name(parameters)
        # Updated to handle cases like:
        # - "MOCKLIB_API mock_parser_t* mock_parser_create(void);" (keyword + space)
        # - "CJSON_PUBLIC(cJSON *) cJSON_DetachItemViaPointer(...);" (keyword + parentheses)
        # More flexible pattern that allows keywords followed by either space or parentheses
        function_pattern = r'(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')(?:\s+[^(]*?\*?\s*|(?:\([^)]*\)\s*))(\w+)\s*\('
        
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Remove comments to avoid false matches
                content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
                content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
                
                # Find all potential function names
                matches = re.findall(function_pattern, content, re.MULTILINE)
                
                for func_name in matches:
                    # Apply prefix filtering if specified
                    if prefixes:
                        if any(func_name.startswith(prefix) for prefix in prefixes):
                            api_function_names.add(func_name)
                    else:
                        api_function_names.add(func_name)
                        
            except Exception as e:
                logger.warning(f"Failed to read header file {file_path}: {e}")
                continue
        
        logger.info(f"Extracted {len(api_function_names)} potential API function names from headers")
        return api_function_names
    
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
    
    def find_usage_in_repo(self, function_name: str, repo_root: str = None) -> Dict[str, List[str]]:
        """
        在仓库中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            repo_root: 仓库根目录，如果为None则使用分析目标路径
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        # 处理repo_root
        if repo_root is None:
            if self.is_single_file_mode:
                repo_root = os.path.dirname(self.analysis_target_path)
            else:
                repo_root = self.analysis_target_path
        
        # 创建FunctionUsageFinder实例
        usage_finder = FunctionUsageFinder(self.config_parser)
        
        return usage_finder.find_usage_in_repo(
            function_name=function_name,
            repo_root=repo_root,
            analyzed_functions=self.all_functions
        )
    
    def search_api_in_documents(self, api_name: str, search_path: str = None, 
                               use_paragraph_extraction: bool = True,
                               target_files: List[str] = None) -> List[Dict]:
        """
        在文档文件中搜索API使用说明
        
        Args:
            api_name: 要搜索的API名称
            search_path: 搜索路径，如果为None则使用分析目标路径
            use_paragraph_extraction: 是否使用段落提取，默认为True
            target_files: 指定要搜索的文件列表，如果为None则搜索所有文档文件
            
        Returns:
            包含API文档信息的列表
        """
        if search_path is None:
            search_path = self.get_analysis_target_path()
        
        results = self.doc_api_searcher.search_api_in_documents(
            api_name, search_path, use_paragraph_extraction=use_paragraph_extraction,
            target_files=target_files
        )
        return [result.to_dict() for result in results]