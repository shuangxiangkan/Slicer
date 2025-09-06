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

    def extract_all_apis(self, output_dir: str, analyzer=None):
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
            
            # 保存API到文件
            api_file_path = os.path.join(output_dir, f"{self.library_name}_apis.txt")
            with open(api_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {self.library_name} Library API Functions\n")
                f.write(f"# Total: {len(unique_api_functions)} functions\n\n")
                
                for _, func_info in unique_api_functions.items():
                    # 写入完整的函数签名
                    f.write(f"{func_info.get_signature()}\n")
                    f.write(f"  // File: {func_info.file_path}:{func_info.start_line}\n\n")
            
            log_info(f"API函数已保存到: {api_file_path}")
            
            # 返回API函数列表
            return list(unique_api_functions.values())
            
        except Exception as e:
            log_error(f"提取API函数时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_and_save_apis(self, output_dir: str, analyzer=None):
        """
        提取API函数并保存到文件，同时返回API函数列表
        
        Args:
            output_dir: API文件的输出目录
            analyzer: RepoAnalyzer实例，如果为None则需要从外部传入
            
        Returns:
            list: API函数列表，每个元素为FunctionInfo对象
        """
        return self.extract_all_apis(output_dir, analyzer)

    def compute_api_usage(self, api_functions, analyzer, output_dir: str):
        """
        计算API函数的usage统计信息并保存结果到文件
        
        Args:
            api_functions: API函数列表，由extract_all_apis返回
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
            api_with_test_usage = 0
            
            # 为每个API函数统计usage
            for i, func in enumerate(api_functions, 1):
                log_info(f"分析函数usage {i}/{len(api_functions)}: {func.name}")
                
                # 查找所有文件中的usage
                all_usage = analyzer.find_usage_in_all_files(function_name=func.name)
                
                # 查找测试文件中的usage
                test_usage = analyzer.find_usage_in_test_files(function_name=func.name)
                
                # 统计详细信息
                usage_details = {
                    'function_name': func.name,
                    'function_signature': func.get_signature(),
                    'has_usage': bool(all_usage),
                    'has_test_usage': bool(test_usage),
                    'total_files': len(all_usage) if all_usage else 0,
                    'test_files': len(test_usage) if test_usage else 0,
                    'all_usage': {},
                    'test_usage': {}
                }
                
                # 处理全局usage详情
                if all_usage:
                    api_with_usage += 1
                    for file_path, callers in all_usage.items():
                        usage_line_numbers = self._get_usage_line_numbers(file_path, func.name)
                        caller_info = []
                        for caller in callers:
                            if isinstance(caller, dict):
                                caller_info.append({
                                    'name': caller.get('name', 'unknown'),
                                    'start_line': caller.get('start_line', 0),
                                    'end_line': caller.get('end_line', 0)
                                })
                            else:
                                caller_info.append({
                                    'name': str(caller),
                                    'start_line': 0,
                                    'end_line': 0
                                })
                        
                        usage_details['all_usage'][file_path] = {
                            'callers': caller_info,
                            'usage_count': len(usage_line_numbers),
                            'usage_locations': usage_line_numbers
                        }
                
                # 处理测试usage详情
                if test_usage:
                    api_with_test_usage += 1
                    for file_path, callers in test_usage.items():
                        usage_line_numbers = self._get_usage_line_numbers(file_path, func.name)
                        caller_info = []
                        for caller in callers:
                            if isinstance(caller, dict):
                                caller_info.append({
                                    'name': caller.get('name', 'unknown'),
                                    'start_line': caller.get('start_line', 0),
                                    'end_line': caller.get('end_line', 0)
                                })
                            else:
                                caller_info.append({
                                    'name': str(caller),
                                    'start_line': 0,
                                    'end_line': 0
                                })
                        
                        usage_details['test_usage'][file_path] = {
                            'callers': caller_info,
                            'usage_count': len(usage_line_numbers),
                            'usage_locations': usage_line_numbers
                        }
                
                usage_results[func.name] = usage_details
            
            # 计算统计信息
            total_apis = len(api_functions)
            usage_rate = (api_with_usage / total_apis) * 100 if total_apis else 0
            test_usage_rate = (api_with_test_usage / total_apis) * 100 if total_apis else 0
            
            # 保存usage结果到文件
            usage_file_path = os.path.join(output_dir, f"{self.library_name}_api_usage.txt")
            with open(usage_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {self.library_name} Library API Usage Analysis\n")
                f.write(f"# Total API Functions: {total_apis}\n")
                f.write(f"# APIs with Usage: {api_with_usage} ({usage_rate:.1f}%)\n")
                f.write(f"# APIs with Test Usage: {api_with_test_usage} ({test_usage_rate:.1f}%)\n\n")
                
                for func_name, details in usage_results.items():
                    f.write(f"Function: {func_name}\n")
                    f.write(f"  Signature: {details['function_signature']}\n")
                    f.write(f"  Has Usage: {details['has_usage']}\n")
                    f.write(f"  Has Test Usage: {details['has_test_usage']}\n")
                    
                    if details['all_usage']:
                        f.write(f"  All Usage ({details['total_files']} files):\n")
                        for file_path, file_info in details['all_usage'].items():
                            f.write(f"    - {file_path}: {file_info['usage_count']} usages\n")
                            f.write(f"      Lines: {file_info['usage_locations']}\n")
                            if file_info['callers']:
                                f.write(f"      Callers: {[c['name'] for c in file_info['callers']]}\n")
                    
                    if details['test_usage']:
                        f.write(f"  Test Usage ({details['test_files']} files):\n")
                        for file_path, file_info in details['test_usage'].items():
                            f.write(f"    - {file_path}: {file_info['usage_count']} usages\n")
                            f.write(f"      Lines: {file_info['usage_locations']}\n")
                            if file_info['callers']:
                                f.write(f"      Callers: {[c['name'] for c in file_info['callers']]}\n")
                    
                    f.write("\n")
            
            log_info(f"API usage分析结果已保存到: {usage_file_path}")
            log_success(f"API usage分析完成，共分析 {total_apis} 个函数，{api_with_usage} 个有usage，{api_with_test_usage} 个有test usage")
            
            return usage_results
            
        except Exception as e:
            log_error(f"计算API usage时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _get_usage_line_numbers(self, file_path, function_name):
        """
        获取函数在文件中的详细usage行号信息
        
        Args:
            file_path: 文件路径
            function_name: 函数名
            
        Returns:
            list: 包含函数名的行号列表
        """
        try:
            # 尝试多种编码方式
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            lines = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            
            if lines is None:
                log_warning(f"无法读取文件 {file_path}: 所有编码都失败")
                return []
            
            usages = []
            for i, line in enumerate(lines, 1):
                if function_name in line:
                    usages.append(i)
            
            return usages
        except Exception as e:
            log_warning(f"读取文件失败 {file_path}: {e}")
            return []

    def compute_api_similarity(self, api_functions, output_dir: str, similarity_threshold: float = 0.2):
        """
        计算API函数之间的相似性并保存结果到文件
        
        Args:
            api_functions: API函数列表，由extract_all_apis返回
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
            
            # 保存相似性结果到文件
            similarity_file_path = os.path.join(output_dir, f"{self.library_name}_api_similarity.txt")
            with open(similarity_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {self.library_name} Library API Similarity Analysis\n")
                f.write(f"# Total API Functions: {len(api_functions)}\n")
                f.write(f"# Similarity Threshold: {similarity_threshold}\n\n")
                
                for func_name, similar_funcs in similarity_results.items():
                    f.write(f"Function: {func_name}\n")
                    if similar_funcs:
                        f.write(f"  Similar functions ({len(similar_funcs)} found):\n")
                        for similar_func, score in similar_funcs:
                            f.write(f"    - {similar_func.name} (similarity: {score:.3f})\n")
                            f.write(f"      Signature: {similar_func.get_signature()}\n")
                    else:
                        f.write("  No similar functions found above threshold\n")
                    f.write("\n")
            
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