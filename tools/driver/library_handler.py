#!/usr/bin/env python3
"""
Library handler for compiling and managing libraries.
"""

import subprocess
import os
from config_parser import ConfigParser
from log import *
from utils import check_afl_instrumentation
from similarity_analyzer import APISimilarityAnalyzer

class LibraryHandler:
    """Handles library operations like compilation."""

    def __init__(self, config_parser: ConfigParser, library_dir: str):
        """
        Initialize LibraryHandler with configuration.
        
        Args:
            config_parser: ConfigParser object with loaded configuration.
            library_dir: Specific library directory path.
        """
        self.config_parser = config_parser
        self.library_name = self.config_parser.get_library_info()['name']
        self.library_dir = library_dir

    def get_all_apis(self, output_dir: str, analyzer=None):
        """
        提取API函数并保存到文件
        
        Args:
            output_dir: API文件的输出目录
            analyzer: RepoAnalyzer实例，如果为None则需要从外部传入
            
        Returns:
            list: API函数列表，每个元素为FunctionInfo对象
        """
        try:
            log_info(f"开始提取 {self.library_name} 库的API函数...")
            
            if analyzer is None:
                raise ValueError("analyzer参数不能为None，请传入配置好的RepoAnalyzer实例")
            
            # 获取API关键字和前缀
            api_config = self.config_parser.get_api_selection()
            api_keywords = api_config.get('keywords', [])
            api_prefix = api_config.get('include_prefix')
            if isinstance(api_prefix, list) and api_prefix:
                api_prefix = api_prefix[0]  # 取第一个前缀
            
            log_info(f"搜索API关键字: {', '.join(api_keywords)}")
            if api_prefix:
                log_info(f"限制函数前缀: '{api_prefix}'")
            
            # 获取头文件配置
            header_files = analyzer.config_parser.get_header_files() if analyzer.config_parser else None
            
            # 直接使用RepoAnalyzer的get_api_functions方法获取API函数
            api_functions = analyzer.get_api_functions(
                api_keyword=api_keywords,
                header_files=header_files,
                api_prefix=api_prefix
            )
            
            # 转换为字典格式（基于函数名去重）
            unique_api_functions = {func_info.name: func_info for func_info in api_functions}
            
            if not unique_api_functions:
                log_warning("未找到API函数")
                return []
            
            log_info(f"找到 {len(unique_api_functions)} 个API函数")
            
            # 保存API到JSON文件
            api_file_path = os.path.join(output_dir, f"{self.library_name}_apis.json")
            
            # 构建JSON数据结构
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": len(unique_api_functions)
                },
                "api_functions": []
            }
            
            # 转换API函数信息为JSON格式
            for _, func_info in unique_api_functions.items():
                json_data["api_functions"].append({
                    "function_name": func_info.name,
                    "function_signature": func_info.get_signature(),
                    "file_path": func_info.file_path,
                    "start_line": func_info.start_line,
                    "end_line": func_info.end_line,
                    "return_type": func_info.return_type,
                    "parameters": [{
                         "name": param.name,
                         "type": param.param_type
                     } for param in func_info.parameter_details] if func_info.parameter_details else []
                })
            
            import json
            with open(api_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"API函数已保存到: {api_file_path}")
            
            # 返回API函数列表
            return list(unique_api_functions.values())
            
        except Exception as e:
            log_error(f"提取API函数时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_api_usage(self, api_functions, analyzer, output_dir: str):
        """
        计算API函数的usage统计信息并保存结果到文件
        
        Args:
            api_functions: API函数列表，由get_all_apis返回
            analyzer: RepoAnalyzer实例，用于查找函数调用
            output_dir: usage结果文件的输出目录
            
        Returns:
            dict: usage统计结果，格式为 {function_name: usage_details}
        """
        try:
            if not api_functions:
                log_warning("没有API函数可用于usage分析")
                return {}
            
            log_info(f"开始统计 {len(api_functions)} 个API函数的usage...")
            
            # 存储所有usage结果
            usage_results = {}
            api_with_usage = 0
            
            # 为每个API函数统计usage
            for i, func in enumerate(api_functions, 1):
                log_info(f"分析函数usage {i}/{len(api_functions)}: {func.name}")
                
                # 查找所有文件中的usage
                all_usage = analyzer.find_usage_in_repo(function_name=func.name)
                
                # 统计详细信息
                usage_details = {
                    'function_name': func.name,
                    'function_signature': func.get_signature(),
                    'has_usage': bool(all_usage),
                    'total_files': len(all_usage) if all_usage else 0,
                    'all_usage': {}
                }
                
                # 处理全局usage详情
                if all_usage:
                    api_with_usage += 1
                    
                    # 先对文件按优先级排序，同一优先级内按caller代码量排序
                    sorted_files = self._sort_files_by_priority(all_usage)
                    
                    for file_path in sorted_files:
                        callers = all_usage[file_path]
                        # 直接使用find_usage_in_repo返回的caller信息，无需重复提取
                        caller_info = []
                        for caller in callers:
                            if isinstance(caller, dict):
                                caller_info.append({
                                    'name': caller.get('name', 'unknown'),
                                    'start_line': caller.get('start_line', 0),
                                    'end_line': caller.get('end_line', 0),
                                    'code': caller.get('code', '')  # 直接使用返回的代码
                                })
                            else:
                                caller_info.append({
                                    'name': str(caller),
                                    'start_line': 0,
                                    'end_line': 0,
                                    'code': ''
                                })
                        
                        # 对同一文件内的caller按代码长度排序
                        caller_info = sorted(caller_info, key=lambda x: len(x.get('code', '')))
                        
                        usage_details['all_usage'][file_path] = {
                            'callers': caller_info,
                            'usage_count': len(callers)
                        }
                
                usage_results[func.name] = usage_details
            
            # 计算统计信息
            total_apis = len(api_functions)
            usage_rate = (api_with_usage / total_apis) * 100 if total_apis else 0
            
            # 保存usage结果到JSON文件
            usage_file_path = os.path.join(output_dir, f"{self.library_name}_api_usage.json")
            
            # 构建JSON数据结构
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": total_apis,
                    "apis_with_usage": api_with_usage,
                    "usage_rate_percentage": round(usage_rate, 1)
                },
                "api_functions": usage_results
            }
            
            import json
            with open(usage_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"API usage分析结果已保存到: {usage_file_path}")
            log_success(f"API usage分析完成，共分析 {total_apis} 个函数，{api_with_usage} 个有usage")
            
            return usage_results
            
        except Exception as e:
            log_error(f"计算API usage时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _sort_files_by_priority(self, all_usage):
        """
        按优先级对文件路径进行排序，同一优先级内按caller代码量排序
        
        Args:
            all_usage: 包含文件路径和对应caller信息的字典
            
        Returns:
            list: 排序后的文件路径列表
        """
        try:
            def get_file_priority_and_code_size(file_path):
                relative_path = self._get_relative_path(file_path)
                path_lower = relative_path.lower()
                
                # 确定优先级
                if 'fuzz' in path_lower:
                    priority = 1  # 最高优先级
                elif any(keyword in path_lower for keyword in ['test', 'demo']):
                    priority = 2  # 第二优先级
                else:
                    priority = 3  # 第三优先级
                
                # 计算该文件中所有caller的总代码量
                callers = all_usage.get(file_path, [])
                total_code_size = 0
                for caller in callers:
                    if isinstance(caller, dict):
                        code = caller.get('code', '')
                        total_code_size += len(code)
                
                # 返回(优先级, 代码量)用于排序
                return (priority, total_code_size)
            
            # 对文件按优先级排序，同一优先级内按代码量排序
            return sorted(all_usage.keys(), key=get_file_priority_and_code_size)
            
        except Exception as e:
            log_warning(f"排序文件时发生错误: {e}")
            return list(all_usage.keys())
    
    def _get_relative_path(self, file_path):
        """
        获取文件相对于库根目录的相对路径
        
        Args:
            file_path: 绝对文件路径
            
        Returns:
            str: 相对于库根目录的相对路径
        """
        try:
            # 从config_parser获取库名
            library_info = self.config_parser.get_library_info()
            library_name = library_info.get('name', '')
            
            if library_name:
                # 查找文件路径中包含库名的部分
                path_parts = file_path.split(os.sep)
                
                # 找到库名在路径中的位置
                library_index = -1
                for i, part in enumerate(path_parts):
                    if part == library_name:
                        library_index = i
                        break
                
                if library_index != -1 and library_index + 1 < len(path_parts):
                    # 返回库根目录之后的相对路径
                    relative_parts = path_parts[library_index + 1:]
                    return os.path.join(*relative_parts)
            
            # 如果无法找到库根目录，返回文件名
            return os.path.basename(file_path)
                
        except Exception as e:
            log_warning(f"获取相对路径时发生错误: {e}")
            return os.path.basename(file_path)

    def get_api_comments(self, api_functions, analyzer, output_dir: str):
        """
        获取API函数的注释信息并保存到文件
        
        Args:
            api_functions: API函数列表，由get_all_apis返回
            analyzer: RepoAnalyzer实例，用于获取函数注释
            output_dir: 注释结果文件的输出目录
            
        Returns:
            dict: 注释信息结果，格式为 {function_name: comment_details}
        """
        try:
            if not api_functions:
                log_warning("没有API函数可用于注释提取")
                return {}
            
            log_info(f"开始提取 {len(api_functions)} 个API函数的注释...")
            
            # 存储所有注释结果
            comments_results = {}
            apis_with_comments = 0
            
            # 为每个API函数提取注释
            for i, func in enumerate(api_functions, 1):
                log_info(f"提取函数注释 {i}/{len(api_functions)}: {func.name}")
                
                # 获取完整注释和摘要信息
                complete_comments = analyzer.get_function_complete_comments(func.name)
                
                # 统计详细信息
                comment_details = {
                    'function_name': func.name,
                    'function_signature': func.get_signature(),
                    'has_comments': bool(complete_comments),
                    'complete_comments': complete_comments or '',
                    'comment_length': len(complete_comments) if complete_comments else 0
                }
                
                if complete_comments:
                    apis_with_comments += 1
                
                comments_results[func.name] = comment_details
            
            # 计算统计信息
            total_apis = len(api_functions)
            comment_rate = (apis_with_comments / total_apis) * 100 if total_apis else 0
            
            # 保存注释结果到JSON文件
            comments_file_path = os.path.join(output_dir, f"{self.library_name}_api_comments.json")
            
            # 构建JSON数据结构
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": total_apis,
                    "apis_with_comments": apis_with_comments,
                    "comment_rate_percentage": round(comment_rate, 1)
                },
                "api_functions": comments_results
            }
            
            import json
            with open(comments_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"API注释分析结果已保存到: {comments_file_path}")
            log_success(f"API注释分析完成，共分析 {total_apis} 个函数，{apis_with_comments} 个有注释")
            
            return comments_results
            
        except Exception as e:
            log_error(f"提取API注释时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_api_documentation(self, api_functions, analyzer, output_dir: str):
        """
        获取API函数在文档中的说明并保存到文件
        
        Args:
            api_functions: API函数列表，由get_all_apis返回
            analyzer: RepoAnalyzer实例，用于搜索API文档
            output_dir: 文档结果文件的输出目录
            
        Returns:
            dict: 文档信息结果，格式为 {function_name: doc_details}
        """
        try:
            if not api_functions:
                log_warning("没有API函数可用于文档搜索")
                return {}
            
            log_info(f"开始搜索 {len(api_functions)} 个API函数的文档说明...")
            
            # 获取文档配置
            doc_config = self.config_parser.get_documentation_config()
            target_files = None
            if doc_config and doc_config.get('target_files'):
                target_files = doc_config['target_files']
                log_info(f"使用配置的目标文档文件: {target_files}")
            else:
                log_info("未配置目标文档文件，将搜索所有文档")
            
            # 存储所有文档结果
            documentation_results = {}
            apis_with_docs = 0
            
            # 为每个API函数搜索文档
            for i, func in enumerate(api_functions, 1):
                log_info(f"搜索函数文档 {i}/{len(api_functions)}: {func.name}")
                
                # 使用RepoAnalyzer的search_api_in_documents方法搜索文档，传入目标文件配置
                doc_results = analyzer.search_api_in_documents(func.name, target_files=target_files)
                
                # 统计详细信息
                doc_details = {
                    'function_name': func.name,
                    'function_signature': func.get_signature(),
                    'has_documentation': bool(doc_results),
                    'documentation_count': len(doc_results),
                    'documentation_sources': []
                }
                
                # 处理找到的文档
                for doc_result in doc_results:
                    doc_source = {
                        'file_path': doc_result['file_path'],
                        'file_name': doc_result['file_name'],
                        'line_number': doc_result['line_number'],
                        'match_type': doc_result['match_type'],
                        'file_type': doc_result['file_type'],
                        'context': doc_result['context']
                    }
                    doc_details['documentation_sources'].append(doc_source)
                
                if doc_results:
                    apis_with_docs += 1
                
                documentation_results[func.name] = doc_details
            
            # 计算统计信息
            total_apis = len(api_functions)
            doc_rate = (apis_with_docs / total_apis) * 100 if total_apis else 0
            
            # 保存文档结果到JSON文件
            docs_file_path = os.path.join(output_dir, f"{self.library_name}_api_documentation.json")
            
            # 构建JSON数据结构
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": total_apis,
                    "apis_with_documentation": apis_with_docs,
                    "documentation_rate_percentage": round(doc_rate, 1)
                },
                "api_functions": documentation_results
            }
            
            import json
            with open(docs_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"API文档分析结果已保存到: {docs_file_path}")
            log_success(f"API文档分析完成，共分析 {total_apis} 个函数，{apis_with_docs} 个有文档说明")
            
            return documentation_results
            
        except Exception as e:
            log_error(f"搜索API文档时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def compute_api_similarity(self, api_functions, output_dir: str, similarity_threshold: float = 0.2):
        """
        计算API函数之间的相似性并保存结果到文件
        
        Args:
            api_functions: API函数列表，由get_all_apis返回
            output_dir: 相似性结果文件的输出目录
            similarity_threshold: 相似度阈值，默认0.2
            
        Returns:
            dict: 相似性分析结果，格式为 {function_name: [(similar_func, similarity_score), ...]}
        """
        try:
            if not api_functions:
                log_warning("没有API函数可用于相似性分析")
                return {}
            
            log_info(f"开始计算 {len(api_functions)} 个API函数的相似性...")
            
            # 初始化相似性分析器
            analyzer = APISimilarityAnalyzer(similarity_threshold=similarity_threshold)
            
            # 存储所有相似性结果
            similarity_results = {}
            
            # 为每个API函数找到最相似的其他函数
            for i, target_func in enumerate(api_functions):
                log_info(f"分析函数相似性 {i+1}/{len(api_functions)}: {target_func.name}")
                
                # 获取与当前函数最相似的其他函数
                similar_funcs = analyzer.find_most_similar_apis(
                    target_function=target_func,
                    all_functions=api_functions,
                    similarity_threshold=similarity_threshold,
                    max_results=3
                )
                
                similarity_results[target_func.name] = similar_funcs
            
            # 保存相似性结果到JSON文件
            similarity_file_path = os.path.join(output_dir, f"{self.library_name}_api_similarity.json")
            
            # 构建JSON数据结构
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": len(api_functions),
                    "similarity_threshold": similarity_threshold
                },
                "similarity_results": {}
            }
            
            # 转换相似性结果为JSON格式
            for func_name, similar_funcs in similarity_results.items():
                json_data["similarity_results"][func_name] = {
                    "similar_functions_count": len(similar_funcs),
                    "similar_functions": []
                }
                
                for similar_func, score in similar_funcs:
                    json_data["similarity_results"][func_name]["similar_functions"].append({
                        "function_name": similar_func.name,
                        "similarity_score": round(score, 3),
                        "function_signature": similar_func.get_signature()
                    })
            
            import json
            with open(similarity_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"相似性分析结果已保存到: {similarity_file_path}")
            log_success(f"API相似性分析完成，共分析 {len(api_functions)} 个函数")
            
            return similarity_results
            
        except Exception as e:
            log_error(f"计算API相似性时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}


    def compile_library(self, library_type: str = "static") -> bool:
        """
        Compiles the library based on the configuration and type.

        Args:
            library_type: Type of library to compile ("static" or "shared"). Defaults to "static".

        Returns:
            True if compilation is successful, False otherwise.
        """
        if library_type not in ["static", "shared"]:
            log_error(f"Invalid library type: {library_type}. Must be 'static' or 'shared'.")
            return False
            
        log_info(f"Starting {library_type} library compilation for {self.library_name}...")
        
        # Get build configuration and command based on type
        if library_type == "static":
            build_config = self.config_parser.get_static_build_config()
            build_command = self.config_parser.get_formatted_static_build_command()
        else:  # shared
            build_config = self.config_parser.get_shared_build_config()
            if build_config is None:
                log_error(f"No shared library build configuration found for {self.library_name}")
                return False
            build_command = self.config_parser.get_formatted_shared_build_command()
            if build_command is None:
                log_error(f"No shared library build command found for {self.library_name}")
                return False
        
        log_info(f"Executing command in {self.library_dir}: {build_command}")
        
        try:
            # Using shell=True because the command is a string with shell features (&&, cd)
            result = subprocess.run(build_command, shell=True, check=True, capture_output=True, text=True, cwd=self.library_dir)
            log_info(f"{library_type.capitalize()} library compilation successful for {self.library_name}.")
            log_info(f"STDOUT:\n{result.stdout}")
            log_success(f"{library_type.capitalize()} library compilation completed successfully.")
            
            # 检查AFL++插桩
            formatted_output = self.config_parser.format_command(build_config['output'])
            library_path = os.path.join(self.library_dir, formatted_output)
            
            if os.path.exists(library_path):
                if check_afl_instrumentation(library_path):
                    log_success(f"AFL++ instrumentation verified successfully for {library_path}")
                else:
                    log_error(f"AFL++ instrumentation verification failed for {library_path}")
                    return False
            else:
                log_error(f"{library_type.capitalize()} library file not found at expected path: {library_path}")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            log_error(f"{library_type.capitalize()} library compilation failed for {self.library_name}.")
            log_error(f"Return code: {e.returncode}")
            log_error(f"STDOUT:\n{e.stdout}")
            log_error(f"STDERR:\n{e.stderr}")
            return False
        except Exception as e:
            log_error(f"An unexpected error occurred during {library_type} library compilation: {e}")
            return False


if __name__ == '__main__':
    # Example usage:
    cjson_config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON.yaml"
    log_info(f"Attempting to compile library using config: {cjson_config_path}")
    
    try:
        config_parser = ConfigParser(cjson_config_path)
        
        # 创建库目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        library_name = config_parser.get_library_info()['name']
        library_dir = os.path.join(base_dir, "Libraries", library_name)
        os.makedirs(library_dir, exist_ok=True)
        
        handler = LibraryHandler(config_parser, library_dir)
        if handler.compile_library("shared"):
        # if handler.compile_library("static"):
            log_success("Library compilation process completed successfully.")
        else:
            log_error("Library compilation process failed.")
    except (FileNotFoundError, ValueError) as e:
        log_error(f"Initialization failed: {e}")