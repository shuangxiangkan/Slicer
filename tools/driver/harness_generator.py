#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness Generator Module

为API函数生成按优先级排序的完整信息
"""

import os
import json
import re
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from log import log_info, log_success, log_warning, log_error
from utils import save_prompt_to_file, save_llm_response_to_file
from libfuzzer2afl import convert_harness_file
from step1_compile_filter import compile_filter
from step2_execution_filter import execution_filter
from step3_coverage_filter import coverage_filter

# Import LLM modules
from llm.base import create_llm_client
from llm.config import LLMConfig
from prompt import PromptGenerator

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class HarnessGenerator:
    """API信息生成器类"""
    
    def __init__(self, config_parser):
        self.config_parser = config_parser
        self.prompt_generator = PromptGenerator(config_parser)
        
        # Initialize LLM client
        try:
            self.llm_config = LLMConfig.from_env()
            self.llm_client = create_llm_client(provider=self.llm_config.default_provider, config=self.llm_config)
            log_info(f"LLM client initialized with provider: {self.llm_config.default_provider}")
        except Exception as e:
            log_warning(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
    
    def generate_harnesses_for_all_apis(self, 
                                       api_functions: List[Any],
                                       api_categories: Dict[str, Any],
                                       usage_results: Dict[str, Any],
                                       similarity_results: Dict[str, Any],
                                       comments_results: Dict[str, Any],
                                       documentation_results: Dict[str, Any],
                                       library_output_dir: str) -> bool:
        """
        生成按优先级排序的API完整信息
        
        Args:
            api_functions: API函数列表
            api_categories: API分类信息
            usage_results: API使用情况结果
            similarity_results: API相似性结果
            comments_results: API注释结果
            documentation_results: API文档结果
            library_output_dir: 输出目录
            
        Returns:
            bool: 生成是否成功
        """
        try:
            log_info("开始生成API信息...")
            
            # 按优先级排序API
            prioritized_apis = self._prioritize_apis(api_functions, api_categories)
            
            # 生成完整的API信息
            api_info_list = []
            
            # 按优先级顺序处理：fuzz -> test_demo -> other -> no_usage
            priority_order = ["fuzz", "test_demo", "other", "no_usage"]
            
            # 注释掉所有API的测试，只测试有fuzz usage的API
            # for priority in priority_order:
            #     api_list = prioritized_apis.get(priority, [])
            #     for api_func in api_list:
            
            # 只处理有fuzz usage的API进行测试
            for priority in priority_order:
                api_list = prioritized_apis.get(priority, [])
                
                # 过滤出有fuzz usage的API
                fuzz_apis = []
                for api_func in api_list:
                    api_name = getattr(api_func, 'name', 'unknown')
                    if api_name in usage_results and usage_results[api_name].get('usage_category') == 'fuzz':
                        fuzz_apis.append(api_func)
                
                if not fuzz_apis:
                    continue
                    
                log_info(f"处理 {priority} 类型API中有fuzz usage的API ({len(fuzz_apis)}个)...")
                
                for api_func in fuzz_apis:
                    api_info = self._collect_api_info(
                        api_func,
                        usage_results,
                        similarity_results,
                        comments_results,
                        documentation_results,
                        priority
                    )
                    api_info_list.append(api_info)
                    
                    # Generate harnesses using LLM (包含prompt生成和保存)
                    if self.llm_client:
                        harness_success = self.generate_harnesses_for_api(api_info, library_output_dir)
                        if harness_success:
                            log_success(f"Successfully generated harnesses for {api_info.get('api_name', 'unknown_api')}")
                        else:
                            log_warning(f"Failed to generate harnesses for {api_info.get('api_name', 'unknown_api')}")
                    else:
                        log_warning(f"LLM client not available, skipping harness generation for {api_info.get('api_name', 'unknown_api')}")
            
            # 保存API信息到JSON文件
            api_info_file = os.path.join(library_output_dir, "api_info_prioritized.json")
            with open(api_info_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_apis": len(api_info_list),
                    "priority_order": priority_order,
                    "apis": api_info_list
                }, f, indent=2, ensure_ascii=False)
            
            log_success(f"API信息生成完成: 共处理 {len(api_info_list)} 个API，保存到 {api_info_file}")
            return True
            
        except Exception as e:
            log_error(f"生成API信息时发生错误: {str(e)}")
            return False
    
    def _prioritize_apis(self, api_functions: List[Any], api_categories: Dict[str, Any]) -> Dict[str, List[Any]]:
        """
        按优先级对API进行分类排序
        
        Returns:
            Dict[str, List[Any]]: 按优先级分类的API列表
        """
        prioritized = {
            "fuzz": [],
            "test_demo": [],
            "other": [],
            "no_usage": []
        }
        
        # 创建API名称到函数对象的映射
        api_name_to_func = {func.name: func for func in api_functions}
        
        # 按分类添加API
        for category, api_names in api_categories.items():
            if category == "with_fuzz":
                for api_name in api_names:
                    if api_name in api_name_to_func:
                        prioritized["fuzz"].append(api_name_to_func[api_name])
            elif category == "with_test_demo":
                for api_name in api_names:
                    if api_name in api_name_to_func:
                        prioritized["test_demo"].append(api_name_to_func[api_name])
            elif category == "with_other_usage":
                for api_name in api_names:
                    if api_name in api_name_to_func:
                        prioritized["other"].append(api_name_to_func[api_name])
            elif category == "no_usage":
                for api_name in api_names:
                    if api_name in api_name_to_func:
                        prioritized["no_usage"].append(api_name_to_func[api_name])
        
        return prioritized
    
    def _collect_api_info(self,
                         api_func: Any,
                         usage_results: Dict[str, Any],
                         similarity_results: Dict[str, Any],
                         comments_results: Dict[str, Any],
                         documentation_results: Dict[str, Any],
                         priority: str) -> Dict[str, Any]:
        """
        收集API完整信息
        """
        api_name = api_func.name
        
        # 获取函数签名
        signature = api_func.get_signature() if hasattr(api_func, 'get_signature') else ''
        
        # 获取usage信息，只取前3个
        usage_info = usage_results.get(api_name, {})
        top_3_usage = self._extract_top_3_usage(usage_info)
        
        # 获取注释信息
        comment_text = ""
        if api_name in comments_results:
            comment_data = comments_results[api_name]
            if comment_data.get('complete_comments'):
                comment_text = comment_data['complete_comments']
        
        # 获取文档信息
        doc_text = self._extract_documentation_summary(documentation_results.get(api_name, {}))
        
        return {
            "api_name": api_name,
            "signature": signature,
            "comments": comment_text,
            "documentation": doc_text,
            "top_3_usage": top_3_usage
        }
    
    def _extract_top_3_usage(self, usage_info):
        """
        从usage信息中提取前3个usage示例
        """
        top_3_usage = []
        if usage_info and usage_info.get('all_usage'):
            all_usage = usage_info['all_usage']
            count = 0
            for file_path, file_usage in all_usage.items():
                if count >= 3:
                    break
                callers = file_usage.get('callers', [])
                for caller in callers:
                    if count >= 3:
                        break
                    usage_example = {
                        "code": caller.get('code', '')
                    }
                    top_3_usage.append(usage_example)
                    count += 1
        return top_3_usage
    
    def _extract_documentation_summary(self, doc_info):
        """
        从文档信息中提取摘要
        """
        if not doc_info or not doc_info.get('documentation_sources'):
            return ""
        
        # 取第一个文档源的context作为摘要
        sources = doc_info['documentation_sources']
        if sources and len(sources) > 0:
            return sources[0].get('context', '')
        
        return ""
    
    def generate_fuzz_harness_prompt(self, api_info: Dict[str, Any]) -> str:
        """为单个API生成fuzz harness的prompt"""
        return self.prompt_generator.generate_fuzz_harness_prompt(api_info)
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract C/C++ code from LLM response"""
        # Try to find code blocks marked with ```c, ```cpp, or ```
        code_patterns = [
            r'```(?:c|cpp|c\+\+)\s*\n(.*?)```',
            r'```\s*\n(.*?)```'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                # Return the first (usually longest) code block
                return matches[0].strip()
        
        # If no code blocks found, return the entire response
        return response.strip()
    
    def _extract_multiple_harnesses(self, response: str) -> List[str]:
        """Extract multiple C/C++ harnesses from LLM response"""
        # Look for code blocks marked with ```c, ```cpp, or ```
        patterns = [
            r'```(?:c|cpp)\s*\n(.*?)```',
            r'```\s*\n(.*?)```'
        ]
        
        harnesses = []
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                harnesses.extend([match.strip() for match in matches])
                break
        
        # If we found harnesses, return up to 3
        if harnesses:
            return harnesses[:3]
        
        # If no code blocks found, try to split by harness comments
        harness_pattern = r'//\s*Harness\s*\d+.*?(?=//\s*Harness\s*\d+|$)'
        harness_matches = re.findall(harness_pattern, response, re.DOTALL | re.IGNORECASE)
        
        if harness_matches:
            return [match.strip() for match in harness_matches[:3]]
        
        # If still no matches, return the entire response as single harness
        return [response.strip()]
    
    def _get_file_extension(self) -> str:
        """Get file extension based on library language"""
        library_info = self.config_parser.get_library_info()
        language = library_info.get('language', 'C').upper()
        return '.cpp' if language == 'C++' else '.c'
    

    def _generate_single_harness(self, api_info: Dict[str, Any], harness_index: int, 
                                harness_libfuzzer_dir: str, harness_afl_dir: str, 
                                library_output_dir: str) -> bool:
        """Generate a single harness for an API"""
        api_name = api_info.get('api_name', 'unknown_api')
        file_ext = self._get_file_extension()
        
        try:
            # Generate prompt
            prompt = self.generate_fuzz_harness_prompt(api_info)
            
            # Call LLM to generate harness
            response = self.llm_client.generate_response(prompt)
            
            # Save LLM response to file
            response_filepath = save_llm_response_to_file(response, library_output_dir, 
                                                        api_name, harness_index)
            log_info(f"LLM response {harness_index} for {api_name} saved to {response_filepath}")
            
            # Extract harness code from response
            harness_code = self._extract_code_from_response(response)
            
            if harness_code.strip():
                harness_filename = f"{api_name}_harness_{harness_index}{file_ext}"
                
                # Save LibFuzzer version
                libfuzzer_filepath = os.path.join(harness_libfuzzer_dir, harness_filename)
                with open(libfuzzer_filepath, 'w', encoding='utf-8') as f:
                    f.write(harness_code)
                log_info(f"Harness {harness_index} for {api_name} saved to {libfuzzer_filepath}")
                
                # Convert to AFL++ version
                afl_filepath = os.path.join(harness_afl_dir, harness_filename)
                if convert_harness_file(libfuzzer_filepath, afl_filepath):
                    log_info(f"AFL++ harness {harness_index} for {api_name} saved to {afl_filepath}")
                    return True
                else:
                    log_warning(f"Failed to convert harness {harness_index} for {api_name} to AFL++ format")
                    # Still count as success if LibFuzzer version was saved
                    return True
            else:
                log_warning(f"Empty harness {harness_index} for {api_name}, skipping")
                return False
                
        except Exception as e:
            log_error(f"Failed to generate harness {harness_index} for {api_name}: {e}")
            return False
    
    def generate_harnesses_for_api(self, api_info: Dict[str, Any], library_output_dir: str) -> bool:
        """Generate multiple harnesses for a single API using parallel execution"""
        if not self.llm_client:
            log_error("LLM client not available, cannot generate harnesses")
            return False
        
        api_name = api_info.get('api_name', 'unknown_api')
        harness_libfuzzer_dir = os.path.join(library_output_dir, api_name, 'harness_libfuzzer')
        harness_afl_dir = os.path.join(library_output_dir, api_name, 'harness')
        
        # Create harness directories if they don't exist
        os.makedirs(harness_libfuzzer_dir, exist_ok=True)
        os.makedirs(harness_afl_dir, exist_ok=True)
        
        # Generate and save prompt (for reference)
        prompt = self.generate_fuzz_harness_prompt(api_info)
        prompt_file = save_prompt_to_file(prompt, library_output_dir, api_name)
        log_info(f"Generated prompt for {api_name} saved to {prompt_file}")
        
        # Generate 3 harnesses in parallel
        success_count = 0
        log_info(f"Generating 3 harnesses for {api_name} in parallel...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit tasks for parallel execution
            future_to_index = {
                executor.submit(self._generate_single_harness, api_info, i, 
                              harness_libfuzzer_dir, harness_afl_dir, library_output_dir): i 
                for i in range(1, 4)
            }
            
            # Collect results
            for future in as_completed(future_to_index):
                harness_index = future_to_index[future]
                try:
                    if future.result():
                        success_count += 1
                        log_info(f"Harness {harness_index} for {api_name} generated successfully")
                    else:
                        log_warning(f"Harness {harness_index} for {api_name} generation failed")
                except Exception as e:
                    log_error(f"Harness {harness_index} for {api_name} generation exception: {e}")
        
        if success_count == 0:
            log_error(f"No valid harnesses generated for {api_name}")
        else:
            # 调用编译过滤器筛选生成的harness
            log_info(f"Starting compile filtering for {api_name}...")
            try:
                # 设置编译过滤的目录
                compile_output_dir = os.path.join(library_output_dir, api_name, 'harness_compiled')
                compile_log_dir = os.path.join(library_output_dir, api_name, 'harness_compiled_logs')
                filtered_harness_dir = os.path.join(library_output_dir, api_name, 'harness_compiled_filtered')
                
                # 执行编译过滤
                compile_successful_harnesses = compile_filter(
                    harness_dir=harness_afl_dir,
                    output_dir=compile_output_dir,
                    log_dir=compile_log_dir,
                    next_stage_dir=filtered_harness_dir,
                    config_parser=self.config_parser
                )
                
                if compile_successful_harnesses:
                    log_success(f"Compile filtering completed for {api_name}: {len(compile_successful_harnesses)} harnesses passed")
                    
                    # 调用执行筛选器筛选编译成功的harness
                    log_info(f"Starting execution filtering for {api_name}...")
                    try:
                        # 设置执行筛选的目录
                        execution_log_dir = os.path.join(library_output_dir, api_name, 'harness_execution_logs')
                        execution_filtered_dir = os.path.join(library_output_dir, api_name, 'harness_execution_filtered')
                        
                        # 从配置文件获取seeds目录路径
                        seeds_valid_dir = self.config_parser.get_seeds_dir()
                        if not seeds_valid_dir:
                            raise ValueError(f"Seeds directory not configured in config file for {api_name}")
                        
                        if not os.path.exists(seeds_valid_dir):
                            raise FileNotFoundError(f"Seeds directory does not exist: {seeds_valid_dir}")
                        
                        # 执行执行筛选（使用execution_log_dir记录执行情况）
                        execution_successful_harnesses = execution_filter(
                            log_dir=execution_log_dir,
                            seeds_valid_dir=seeds_valid_dir,
                            next_stage_dir=execution_filtered_dir,
                            compile_log_dir=compile_log_dir
                        )
                        
                        if execution_successful_harnesses:
                            log_success(f"Execution filtering completed for {api_name}: {len(execution_successful_harnesses)} harnesses passed")
                            
                            # 调用覆盖率筛选器筛选执行成功的harness
                            log_info(f"Starting coverage filtering for {api_name}...")
                            try:
                                # 设置覆盖率筛选的目录
                                # 注意：step2_successful_harnesses.json文件在execution_logs目录中
                                execution_log_dir = os.path.join(library_output_dir, api_name, 'harness_execution_logs')
                                coverage_log_dir = os.path.join(library_output_dir, api_name, 'harness_coverage_logs')
                                coverage_filtered_dir = os.path.join(library_output_dir, api_name, 'harness_coverage_filtered')
                                
                                # 从配置文件获取seeds目录路径
                                seeds_valid_dir = self.config_parser.get_seeds_dir()
                                if not seeds_valid_dir:
                                    raise ValueError(f"Seeds directory not configured in config file for {api_name}")
                                
                                if not os.path.exists(seeds_valid_dir):
                                    raise FileNotFoundError(f"Seeds directory does not exist: {seeds_valid_dir}")
                                
                                # 从配置文件获取dict文件路径（如果有的话）
                                dict_file = self.config_parser.get_dictionary_file()
                                if dict_file and not os.path.exists(dict_file):
                                    log_warning(f"Dictionary file does not exist: {dict_file}, proceeding without dict")
                                    dict_file = None
                                
                                # 如果有dict文件，可以在后续的fuzz过程中使用
                                if dict_file:
                                    log_info(f"Dictionary file available for fuzzing: {dict_file}")
                                
                                # 执行覆盖率筛选
                                # 使用execution_log_dir来读取step2_successful_harnesses.json
                                # 使用coverage_log_dir来保存step3结果
                                coverage_successful_harnesses = coverage_filter(
                                    log_dir=execution_log_dir,
                                    seeds_valid_dir=seeds_valid_dir,
                                    final_dir=coverage_filtered_dir,
                                    max_harnesses=1,  # 只选择1个最佳harness
                                    dict_file=dict_file,  # 传递dict文件路径
                                    coverage_log_dir=coverage_log_dir  # 指定覆盖率日志保存目录
                                )
                                
                                if coverage_successful_harnesses:
                                    log_success(f"Coverage filtering completed for {api_name}: {len(coverage_successful_harnesses)} harnesses passed")
                                else:
                                    log_warning(f"No harnesses passed coverage filtering for {api_name}")
                                    
                            except Exception as e:
                                log_error(f"Coverage filtering failed for {api_name}: {e}")
                        else:
                            log_warning(f"No harnesses passed execution filtering for {api_name}")
                            
                    except Exception as e:
                        log_error(f"Execution filtering failed for {api_name}: {e}")
                else:
                    log_warning(f"No harnesses passed compile filtering for {api_name}")
                    
            except Exception as e:
                log_error(f"Compile filtering failed for {api_name}: {e}")
        
        return success_count > 0