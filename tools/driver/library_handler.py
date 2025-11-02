#!/usr/bin/env python3
"""
Library handler for compiling and managing libraries.
"""

import subprocess
import os
import json
import asyncio
import concurrent.futures
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path for llm module imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config_parser import ConfigParser
from log import *
from utils import check_afl_instrumentation, resolve_target_files

from prompt import PromptGenerator

# Import LLM modules
from llm.base import create_llm_client
from llm.config import LLMConfig

class LibraryHandler:
    """Handles library operations like compilation."""

    def __init__(self, config_parser: ConfigParser):
        """
        Initialize LibraryHandler with configuration.
        
        Args:
            config_parser: ConfigParser object with loaded configuration.
        """
        self.config_parser = config_parser
        self.library_name = self.config_parser.get_library_info()['name']
        self.library_dir = self.config_parser.get_libraries_dir()
        
        # Initialize prompt generator
        self.prompt_generator = PromptGenerator(config_parser)
        
        # Initialize LLM client
        try:
            self.llm_config = LLMConfig.from_env()
            self.llm_client = create_llm_client(config=self.llm_config)
            log_info(f"LLM client initialized with provider: {self.llm_client.provider}")
        except Exception as e:
            log_warning(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
        
        # Initialize documentation analysis cost statistics
        self.doc_analysis_stats = {
            'total_documents_processed': 0,
            'total_llm_calls': 0,
            'successful_analyses': 0,
            'failed_analyses': 0
        }

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
            api_macros = api_config.get('api_macros', [])
            api_prefixes = api_config.get('api_prefix', [])
            
            log_info(f"搜索API宏: {', '.join(api_macros)}")
            if api_prefixes:
                log_info(f"限制函数前缀: {', '.join(api_prefixes)}")
            
            # 获取头文件配置 - 使用展开的headers字段用于API提取
            header_files = self.config_parser.get_expanded_header_file_paths() if self.config_parser else None
            
            # 直接使用RepoAnalyzer的get_api_functions方法获取API函数
            api_functions = analyzer.get_api_functions(
                api_macros=api_macros,
                api_prefix=api_prefixes,
                header_files=header_files
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
            
            # 存储API分类信息
            api_categories = {
                'with_fuzz': [],
                'with_test_demo': [],
                'with_other_usage': [],
                'no_usage': []
            }
            
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
                    
                    # 分析API的usage类型并分类
                    api_category = self._categorize_api_usage(all_usage)
                    if api_category == 'fuzz':
                        api_categories['with_fuzz'].append(func.name)
                    elif api_category == 'test_demo':
                        api_categories['with_test_demo'].append(func.name)
                    else:
                        api_categories['with_other_usage'].append(func.name)
                    
                    # 将分类信息添加到usage详情中
                    usage_details['usage_category'] = api_category
                    
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
                
                else:
                    # 没有usage的API
                    api_categories['no_usage'].append(func.name)
                    usage_details['usage_category'] = 'no_usage'
                
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
                "api_categories": {
                    "with_fuzz": {
                        "count": len(api_categories['with_fuzz']),
                        "apis": api_categories['with_fuzz']
                    },
                    "with_test_demo": {
                        "count": len(api_categories['with_test_demo']),
                        "apis": api_categories['with_test_demo']
                    },
                    "with_other_usage": {
                        "count": len(api_categories['with_other_usage']),
                        "apis": api_categories['with_other_usage']
                    },
                    "no_usage": {
                        "count": len(api_categories['no_usage']),
                        "apis": api_categories['no_usage']
                    }
                },
                "api_functions": usage_results
            }
            
            import json
            with open(usage_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"API usage分析结果已保存到: {usage_file_path}")
            log_success(f"API usage分析完成，共分析 {total_apis} 个函数，{api_with_usage} 个有usage")
            log_info(f"API分类统计: Fuzz({len(api_categories['with_fuzz'])}), Test/Demo({len(api_categories['with_test_demo'])}), Other({len(api_categories['with_other_usage'])}), No Usage({len(api_categories['no_usage'])})")
            
            return usage_results, api_categories
            
        except Exception as e:
            log_error(f"计算API usage时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}, {}
    
    def _categorize_api_usage(self, all_usage):
        """
        根据usage文件路径分析API的使用类型
        
        分类逻辑：
        - fuzz: 文件路径包含'fuzz'关键词
        - test_demo: 文件路径包含测试、演示、示例、文档等相关关键词
          包括: 'test', 'demo', 'example', 'sample', 'benchmark', 'unit', 'usage', 'main', 'driver', 'harness'
        - other: 其他类型的使用
        
        Args:
            all_usage: 包含文件路径和对应caller信息的字典
            
        Returns:
            str: API分类 ('fuzz', 'test_demo', 'other')
        """
        try:
            has_fuzz = False
            has_test_demo = False
            
            for file_path in all_usage.keys():
                relative_path = self._get_relative_path(file_path)
                path_lower = relative_path.lower()
                
                # 检查是否有fuzz相关的usage
                if 'fuzz' in path_lower:
                    has_fuzz = True
                
                # 检查是否有test/demo相关的usage
                test_demo_keywords = [
                    'test', 'demo', 'example', 'sample', 'benchmark', 
                    'unit', 'usage', 'main', 'driver', 'harness'
                ]
                if any(keyword in path_lower for keyword in test_demo_keywords):
                    has_test_demo = True
            
            # 优先级：fuzz > test_demo > other
            if has_fuzz:
                return 'fuzz'
            elif has_test_demo:
                return 'test_demo'
            else:
                return 'other'
                
        except Exception as e:
            log_warning(f"分类API usage时发生错误: {e}")
            return 'other'
    
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
        使用LLM并行分析文档，提取API函数的使用描述
        
        Args:
            api_functions: API函数列表
            analyzer: RepoAnalyzer实例
            output_dir: 输出目录
            
        Returns:
            dict: API文档结果
        """
        try:
            if not api_functions:
                log_warning("没有API函数可用于文档分析")
                return {}
            
            if not self.llm_client:
                log_error("LLM客户端未初始化，无法进行文档分析")
                return {}
            
            log_info(f"开始并行分析 {len(api_functions)} 个API函数的文档...")
            
            # 获取文档配置和内容
            doc_config = self.config_parser.get_documentation_config()
            target_files = doc_config.get('target_files', []) if doc_config else []
            document_contents = self._get_document_contents(analyzer, target_files)
            
            if not document_contents:
                log_warning("未找到任何文档文件")
                return {}
            
            # 统计处理的文档数量
            self.doc_analysis_stats['total_documents_processed'] = len(document_contents)
            
            # 并行分析所有文档
            api_docs = asyncio.run(self._parallel_analyze_documents(document_contents))
            
            # 合并结果并保存
            result = self._save_documentation_results(api_docs, api_functions, output_dir)
            
            # 生成文档分析成本报告
            self._generate_doc_analysis_cost_report(output_dir)
            
            log_success(f"文档分析完成，共处理 {len(document_contents)} 个文档文件")
            return result
            
        except Exception as e:
            log_error(f"文档分析时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _get_document_contents(self, analyzer, target_files: List[str] = None) -> Dict[str, str]:
        """获取文档文件内容"""
        try:
            document_contents = {}
            
            if target_files:
                # 处理指定文件 - 获取具体的库目录
                target_library_dir = self.config_parser.get_target_library_dir()
                resolved_files = resolve_target_files(target_files, target_library_dir)
                
                for file_path in resolved_files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                                if content:
                                    document_contents[file_path] = content
                        except Exception as e:
                            log_warning(f"读取文件 {file_path} 失败: {e}")
            else:
                # 获取所有文档文件
                search_path = analyzer.get_analysis_target_path()
                all_doc_files = analyzer.doc_api_searcher._find_document_files(search_path, recursive=True)
                for file_path in all_doc_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content:
                                document_contents[file_path] = content
                    except:
                        continue
            
            return document_contents
        except Exception as e:
            log_error(f"获取文档内容失败: {e}")
            return {}
    


    async def _parallel_analyze_documents(self, document_contents: Dict[str, str]) -> Dict[str, Any]:
        """并行分析所有文档"""
        try:
            all_apis = {}
            
            # 使用线程池并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                
                for file_path, content in document_contents.items():
                    future = executor.submit(self._analyze_single_document, content)
                    futures.append(future)
                
                # 收集结果
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            # 合并API结果
                            for api_name, api_info in result.items():
                                if api_name not in all_apis:
                                    all_apis[api_name] = api_info
                                else:
                                    # 合并描述
                                    existing_desc = all_apis[api_name].get('description', '')
                                    new_desc = api_info.get('description', '')
                                    if new_desc and new_desc not in existing_desc:
                                        all_apis[api_name]['description'] = f"{existing_desc} {new_desc}".strip()
                    except Exception as e:
                        log_warning(f"处理文档时发生错误: {e}")
            
            return all_apis
        except Exception as e:
            log_error(f"并行分析文档失败: {e}")
            return {}

    def _split_document_into_chunks(self, content: str, max_tokens: int = 40000) -> List[str]:
        """将大文档分割成小块"""
        # 估算当前内容的token数（粗略估算：1 token ≈ 4 字符）
        estimated_tokens = len(content) // 4
        
        if estimated_tokens <= max_tokens:
            return [content]
        
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = len(line) // 4  # 直接计算，不需要单独函数
            
            # 如果添加这一行会超过限制，保存当前块并开始新块
            if current_tokens + line_tokens > max_tokens and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        # 添加最后一块
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _analyze_single_document(self, content: str) -> Dict[str, Any]:
        """分析单个文档（支持大文档分块处理）"""
        try:
            # 检查文档大小，如果太大则分块处理
            estimated_tokens = len(content) // 4  # 粗略估算：1 token ≈ 4 字符
            max_safe_tokens = 40000  # 保守估计，留出提示词和响应的空间
            
            if estimated_tokens > max_safe_tokens:
                log_info(f"文档过大 ({estimated_tokens} tokens)，将分块处理")
                chunks = self._split_document_into_chunks(content, max_safe_tokens)
                
                # 分别分析每个块并合并结果
                all_apis = {}
                for i, chunk in enumerate(chunks):
                    log_info(f"分析文档块 {i+1}/{len(chunks)}")
                    chunk_result = self._analyze_document_chunk(chunk)
                    
                    # 合并API结果
                    for api_name, api_info in chunk_result.items():
                        if api_name not in all_apis:
                            all_apis[api_name] = api_info
                        else:
                            # 合并描述
                            existing_desc = all_apis[api_name].get('description', '')
                            new_desc = api_info.get('description', '')
                            if new_desc and new_desc not in existing_desc:
                                all_apis[api_name]['description'] = f"{existing_desc} {new_desc}".strip()
                
                return all_apis
            else:
                # 文档不大，直接处理
                return self._analyze_document_chunk(content)
                
        except Exception as e:
            log_warning(f"分析文档失败: {e}")
            self.doc_analysis_stats['failed_analyses'] += 1
            return {}
    
    def _analyze_document_chunk(self, content: str) -> Dict[str, Any]:
        """分析单个文档块"""
        try:
            # 生成提示
            prompt = self.prompt_generator.generate_api_documentation_extraction_prompt(content, [])
            
            # 调用LLM并统计成本
            self.doc_analysis_stats['total_llm_calls'] += 1
            response = self.llm_client.generate_response(prompt)
            
            if response:
                # 解析JSON
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    self.doc_analysis_stats['successful_analyses'] += 1
                    return result.get('apis', {})
            
            self.doc_analysis_stats['failed_analyses'] += 1
            return {}
        except Exception as e:
            log_warning(f"分析文档块失败: {e}")
            self.doc_analysis_stats['failed_analyses'] += 1
            return {}

    def _save_documentation_results(self, api_docs: Dict[str, Any], api_functions: List, output_dir: str) -> Dict[str, Any]:
        """保存文档分析结果"""
        try:
            # 合并结果
            results = {}
            apis_with_docs = 0
            
            for func in api_functions:
                func_name = func.name
                has_doc = func_name in api_docs
                
                results[func_name] = {
                    'function_name': func_name,
                    'has_documentation': has_doc,
                    'description': api_docs.get(func_name, {}).get('description', '') if has_doc else ''
                }
                
                if has_doc:
                    apis_with_docs += 1
            
            # 保存到文件
            total_apis = len(api_functions)
            doc_rate = (apis_with_docs / total_apis) * 100 if total_apis else 0
            
            docs_file_path = os.path.join(output_dir, f"{self.library_name}_api_documentation.json")
            json_data = {
                "library_name": self.library_name,
                "analysis_summary": {
                    "total_api_functions": total_apis,
                    "apis_with_documentation": apis_with_docs,
                    "documentation_rate_percentage": round(doc_rate, 1)
                },
                "api_functions": results
            }
            
            with open(docs_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            log_info(f"文档分析结果已保存到: {docs_file_path}")
            return results
            
        except Exception as e:
            log_error(f"保存结果失败: {e}")
            return {}

    def compile_library(self, library_type: str = "static") -> bool:
        """
        Compiles the library based on the configuration and type.
        If the library is already compiled and passes verification, skips compilation.

        Args:
            library_type: Type of library to compile ("static" or "shared"). Defaults to "static".

        Returns:
            True if compilation is successful or library already exists and passes verification, False otherwise.
        """
        if library_type not in ["static", "shared"]:
            log_error(f"Invalid library type: {library_type}. Must be 'static' or 'shared'.")
            return False
        
        # Validate fuzzing configuration before compilation
        if not self._validate_fuzzing_config():
            return False
        
        # Get build configuration
        if library_type == "static":
            build_config = self.config_parser.get_static_build_config()
        else:  # shared
            build_config = self.config_parser.get_shared_build_config()
            if build_config is None:
                log_error(f"No shared library build configuration found for {self.library_name}")
                return False
        
        # 首先检查是否已有编译产物且验证通过
        log_info(f"Checking existing {library_type} library for {self.library_name}...")
        if self._check_existing_library(library_type, build_config):
            log_success(f"Existing {library_type} library found and verified for {self.library_name}, skipping compilation.")
            return True
        
        # 如果不存在或验证失败，进行编译
        log_info(f"Starting {library_type} library compilation for {self.library_name}...")
        
        # Get build command
        if library_type == "static":
            build_command = self.config_parser.get_formatted_static_build_command()
        else:  # shared
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
            
            # 验证生成的库文件和头文件路径
            if not self._verify_build_outputs(library_type, build_config):
                log_error(f"Build output verification failed for {library_type} library")
                return False
            
            # 检查AFL++插桩
            if not self._verify_afl_instrumentation(library_type):
                log_error(f"AFL++ instrumentation verification failed for {library_type} library")
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
    
    def _validate_fuzzing_config(self) -> bool:
        """
        验证fuzzing配置，包括seeds目录和dictionary文件
        
        Returns:
            True if fuzzing configuration is valid, False otherwise.
        """
        log_info("Validating fuzzing configuration...")
        
        # Check seeds directory
        seeds_dir = self.config_parser.get_seeds_dir()
        if not seeds_dir:
            log_error("Seeds directory not configured in config file")
            return False
        
        if not os.path.exists(seeds_dir):
            log_error(f"Seeds directory does not exist: {seeds_dir}")
            return False
        
        if not os.path.isdir(seeds_dir):
            log_error(f"Seeds path is not a directory: {seeds_dir}")
            return False
        
        # Check if seeds directory has any files
        seed_files = [f for f in os.listdir(seeds_dir) if os.path.isfile(os.path.join(seeds_dir, f))]
        if not seed_files:
            log_error(f"Seeds directory is empty: {seeds_dir}")
            return False
        
        log_success(f"Seeds directory validated: {seeds_dir} (found {len(seed_files)} seed files)")
        
        # Check dictionary file (optional)
        dictionary_file = self.config_parser.get_dictionary_file()
        if dictionary_file:
            if os.path.exists(dictionary_file):
                log_success(f"Dictionary file found: {dictionary_file}")
            else:
                log_warning(f"Dictionary file configured but not found: {dictionary_file}")
        else:
            log_info("No dictionary file configured")
        
        return True
    
    def _check_existing_library(self, library_type: str, build_config: dict) -> bool:
        """
        检查现有库是否存在且通过所有验证
        
        Args:
            library_type: 库类型 ("static" 或 "shared")
            build_config: 构建配置字典
            
        Returns:
            True if existing library exists and passes all verifications, False otherwise.
        """
        try:
            # 验证构建输出（预检查模式，使用温和的日志级别）
            if not self._verify_build_outputs(library_type, build_config, is_precheck=True):
                return False
            
            # 验证AFL++插桩
            if not self._verify_afl_instrumentation(library_type):
                return False
            
            return True
        except Exception as e:
            log_info(f"Existing library check failed: {e}")
            return False
    
    def _verify_afl_instrumentation(self, library_type: str) -> bool:
        """
        验证AFL++插桩
        
        Args:
            library_type: 库类型 ("static" 或 "shared")
            
        Returns:
            True if AFL++ instrumentation is verified, False otherwise.
        """
        try:
            library_path = self.config_parser.get_library_file_path(library_type)
        except Exception as e:
            log_error(f"Failed to get library file path for AFL++ verification: {e}")
            return False
        
        if not os.path.exists(library_path):
            log_error(f"{library_type.capitalize()} library file not found at expected path: {library_path}")
            return False
        
        if check_afl_instrumentation(library_path):
            log_success(f"AFL++ instrumentation verified successfully for {library_path}")
            return True
        else:
            log_error(f"AFL++ instrumentation verification failed for {library_path}")
            return False
    
    def _verify_build_outputs(self, library_type: str, build_config: dict, is_precheck: bool = False) -> bool:
        """
        验证编译后生成的库文件和头文件路径是否正确
        
        Args:
            library_type: 库类型 ("static" 或 "shared")
            build_config: 构建配置字典
            is_precheck: 是否为预检查模式，预检查时使用更温和的日志级别
            
        Returns:
            True if all required files exist at expected paths, False otherwise.
        """
        log_info(f"Verifying build outputs for {library_type} library...")
        
        # 验证库文件路径
        try:
            library_abs_path = self.config_parser.get_library_file_path(library_type)
        except Exception as e:
            if is_precheck:
                log_info(f"Failed to get library file path from configuration: {e}")
            else:
                log_error(f"Failed to get library file path from configuration: {e}")
                log_error("Please check your configuration file for correct library build settings")
            return False
        
        if not os.path.exists(library_abs_path):
            if is_precheck:
                log_info(f"Library file not found (will compile): {library_abs_path}")
            else:
                log_error(f"Library file not found: {library_abs_path}")
                log_error("Please check your configuration file - the library output path may be incorrect")
            return False
        
        log_success(f"Library file verified: {library_abs_path}")
        
        # 验证头文件路径 (使用编译时需要的头文件路径)
        try:
            header_file_paths = self.config_parser.get_compilation_header_file_paths()
            if header_file_paths:
                for header_abs_path in header_file_paths:
                    if not os.path.exists(header_abs_path):
                        if is_precheck:
                            log_info(f"Compilation header file not found (will compile): {header_abs_path}")
                        else:
                            log_error(f"Compilation header file not found: {header_abs_path}")
                            log_error("Please check your configuration file - the header_include and header_folder paths may be incorrect")
                        return False
                    
                    log_success(f"Compilation header file verified: {header_abs_path}")
        except Exception as e:
            if is_precheck:
                log_info(f"Failed to get compilation header file paths from configuration: {e}")
            else:
                log_error(f"Failed to get compilation header file paths from configuration: {e}")
                log_error("Please check your configuration file for correct header_include and header_folder settings")
            return False
        
        log_success(f"All build outputs verified successfully for {library_type} library")
        return True

    def _generate_doc_analysis_cost_report(self, output_dir: str):
        """生成文档分析成本报告"""
        try:
            # 获取LLM成本信息
            llm_cost_info = self.llm_client.get_total_cost() if self.llm_client else None
            
            # 构建成本报告 - 格式与harness生成报告一致
            cost_report = {
                "documentation_analysis_summary": {
                    "total_documents_processed": self.doc_analysis_stats['total_documents_processed'],
                    "total_llm_calls": self.doc_analysis_stats['total_llm_calls'],
                    "successful_analyses": self.doc_analysis_stats['successful_analyses'],
                    "failed_analyses": self.doc_analysis_stats['failed_analyses'],
                    "success_rate": (self.doc_analysis_stats['successful_analyses'] / 
                                   max(self.doc_analysis_stats['total_documents_processed'], 1)) * 100
                },
                "llm_cost_details": {
                    "provider": self.llm_client.provider if hasattr(self, 'llm_client') and self.llm_client else "unknown",
                    "model": getattr(self.llm_config, f"{self.llm_client.provider}_model", "unknown") if hasattr(self, 'llm_client') and self.llm_client and hasattr(self, 'llm_config') else "unknown",
                    "input_tokens": llm_cost_info.input_tokens if llm_cost_info else 0,
                    "output_tokens": llm_cost_info.output_tokens if llm_cost_info else 0,
                    "total_tokens": llm_cost_info.total_tokens if llm_cost_info else 0,
                    "total_cost_usd": llm_cost_info.cost_usd if llm_cost_info else 0.0,
                    "total_requests": llm_cost_info.requests_count if llm_cost_info else 0
                },
                "cost_breakdown": {
                    "cost_per_document": (llm_cost_info.cost_usd / max(self.doc_analysis_stats['total_documents_processed'], 1)) if llm_cost_info else 0.0,
                    "cost_per_successful_analysis": (llm_cost_info.cost_usd / max(self.doc_analysis_stats['successful_analyses'], 1)) if llm_cost_info else 0.0,
                    "average_tokens_per_call": (llm_cost_info.total_tokens / max(self.doc_analysis_stats['total_llm_calls'], 1)) if llm_cost_info else 0.0
                }
            }
            
            # 保存成本报告
            cost_report_path = os.path.join(output_dir, f"{self.library_name}_doc_analysis_cost_report.json")
            with open(cost_report_path, 'w', encoding='utf-8') as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)
            
            # 记录成本摘要
            log_info(f"文档分析成本报告已保存到: {cost_report_path}")
            if llm_cost_info:
                log_success(f"文档分析成本报告:")
                log_info(f"  - 处理文档数量: {self.doc_analysis_stats['total_documents_processed']}")
                log_info(f"  - 成功分析: {self.doc_analysis_stats['successful_analyses']}, 失败: {self.doc_analysis_stats['failed_analyses']}")
                log_info(f"  - LLM调用次数: {self.doc_analysis_stats['total_llm_calls']}")
                log_info(f"  - 总token数: {llm_cost_info.total_tokens:,} (输入: {llm_cost_info.input_tokens:,}, 输出: {llm_cost_info.output_tokens:,})")
                log_info(f"  - 总成本: ${llm_cost_info.cost_usd:.4f} USD")
                log_info(f"  - 平均每个文档成本: ${cost_report['cost_breakdown']['cost_per_document']:.4f} USD")
                log_info(f"  - 平均每次成功分析成本: ${cost_report['cost_breakdown']['cost_per_successful_analysis']:.4f} USD")
                log_success(f"详细成本报告已保存到: {cost_report_path}")
            
        except Exception as e:
            log_error(f"生成文档分析成本报告失败: {e}")

if __name__ == '__main__':
    # Example usage:
    cjson_config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON/cJSON.yaml"
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