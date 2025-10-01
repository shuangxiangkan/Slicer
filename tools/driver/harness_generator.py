#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness Generator Module

为API函数生成按优先级排序的完整信息
"""

import os
import json
import shutil
import subprocess
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from log import log_info, log_success, log_warning, log_error
from utils import save_prompt_to_file, save_llm_response_to_file, extract_code_from_response, get_file_extension
from libfuzzer2afl import convert_harness_file
from step1_compile_filter import create_compile_utils
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
            self.llm_client = create_llm_client(config=self.llm_config)
            log_info(f"LLM client initialized with provider: {self.llm_client.provider}")
        except Exception as e:
            log_warning(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
        
        # Initialize cost tracking
        self.harness_generation_stats = {
            'total_apis_processed': 0,
            'total_harnesses_generated': 0,
            'total_llm_calls': 0,
            'successful_harnesses': 0,
            'failed_harnesses': 0
        }
    
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
                    
                    # Update API processing statistics
                    self.harness_generation_stats['total_apis_processed'] += 1
                    
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
            
            # Generate and save cost report
            self._generate_cost_report(library_output_dir)
            
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
        top_n_usage = self._extract_top_usage(usage_info)
        
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
            "top_n_usage": top_n_usage
        }
    
    def _extract_top_usage(self, usage_info, max_count=3):
        """
        从usage信息中提取指定数量的usage示例
        按照原有顺序选择前max_count个示例
        
        Args:
            usage_info: usage信息字典
            max_count: 最大提取数量，默认为3
        """
        top_usage = []
        if usage_info and usage_info.get('all_usage'):
            all_usage = usage_info['all_usage']
            
            # 按照原有顺序遍历，选择前max_count个示例
            for file_path, file_usage in all_usage.items():
                if len(top_usage) >= max_count:
                    break
                    
                callers = file_usage.get('callers', [])
                for caller in callers:
                    if len(top_usage) >= max_count:
                        break
                        
                    code = caller.get('code', '')
                    top_usage.append({
                        "code": code
                    })
        
        return top_usage
    
    def _extract_documentation_summary(self, doc_info):
        """
        从文档信息中提取摘要
        """
        if not doc_info:
            return ""
        
        # 从API文档结果中提取description字段
        if doc_info.get('has_documentation') and doc_info.get('description'):
            return doc_info['description']
        
        return ""

    def _generate_single_harness(self, api_info: Dict[str, Any], harness_index: int, 
                                harness_libfuzzer_dir: str, harness_afl_dir: str, 
                                library_output_dir: str, max_retries: int = 3) -> bool:
        """Generate a single harness for an API with compilation verification and retry mechanism"""
        api_name = api_info.get('api_name', 'unknown_api')
        file_ext = get_file_extension(self.config_parser)
        
        # Import compile utils for verification
        compile_utils = create_compile_utils(self.config_parser)
        
        for attempt in range(max_retries):
            try:
                log_info(f"Generating harness {harness_index} for {api_name} (attempt {attempt + 1}/{max_retries})")
                
                # Generate prompt (either initial or fix prompt)
                if attempt == 0:
                    prompt = self.prompt_generator.generate_fuzz_harness_prompt(api_info)
                    prompt_type = "initial"
                else:
                    # Use fix prompt with previous code and error
                    prompt = self.prompt_generator.generate_fix_harness_prompt(api_info, failed_code, compile_error)
                    prompt_type = "fix"
                
                # Save prompt to file for each attempt
                prompt_file = save_prompt_to_file(prompt, library_output_dir, 
                                                api_name, f"{harness_index}_attempt_{attempt + 1}_{prompt_type}")
                log_info(f"Generated {prompt_type} prompt for {api_name} harness {harness_index} attempt {attempt + 1} saved to {prompt_file}")
                
                # Call LLM to generate harness
                response = self.llm_client.generate_response(prompt)
                
                # Update LLM call statistics
                self.harness_generation_stats['total_llm_calls'] += 1
                
                # Save LLM response to file
                response_filepath = save_llm_response_to_file(response, library_output_dir, 
                                                            api_name, f"{harness_index}_attempt_{attempt + 1}")
                log_info(f"LLM response {harness_index} attempt {attempt + 1} for {api_name} saved to {response_filepath}")
                
                # Extract harness code from response
                harness_code = extract_code_from_response(response)
                
                if not harness_code.strip():
                    log_warning(f"Empty harness {harness_index} for {api_name} on attempt {attempt + 1}, retrying...")
                    continue
                
                # Save temporary LibFuzzer file and convert to AFL++
                temp_harness_filename = f"{api_name}_harness_{harness_index}_temp{file_ext}"
                temp_libfuzzer_filepath = os.path.join(harness_libfuzzer_dir, temp_harness_filename)
                temp_afl_filepath = os.path.join(harness_afl_dir, temp_harness_filename)
                
                with open(temp_libfuzzer_filepath, 'w', encoding='utf-8') as f:
                    f.write(harness_code)
                
                # Convert to AFL++ format for testing
                if not convert_harness_file(temp_libfuzzer_filepath, temp_afl_filepath):
                    log_warning(f"Failed to convert harness {harness_index} attempt {attempt + 1} to AFL++ format, retrying...")
                    # Clean up temporary files
                    try:
                        os.remove(temp_libfuzzer_filepath)
                    except:
                        pass
                    continue
                
                # Test compilation of AFL++ version
                log_info(f"Testing AFL++ compilation for harness {harness_index} attempt {attempt + 1}...")
                compile_success, binary_path, temp_dir = compile_utils.compile_harness_in_temp(
                    temp_afl_filepath, "verification"
                )
                
                # Clean up temporary compilation files
                if temp_dir:
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    except:
                        pass
                
                if compile_success:
                    # Compilation successful, save final files
                    harness_filename = f"{api_name}_harness_{harness_index}{file_ext}"
                    
                    # Save LibFuzzer version
                    libfuzzer_filepath = os.path.join(harness_libfuzzer_dir, harness_filename)
                    with open(libfuzzer_filepath, 'w', encoding='utf-8') as f:
                        f.write(harness_code)
                    log_success(f"Harness {harness_index} for {api_name} saved to {libfuzzer_filepath}")
                    
                    # Convert to AFL++ version
                    afl_filepath = os.path.join(harness_afl_dir, harness_filename)
                    if convert_harness_file(libfuzzer_filepath, afl_filepath):
                        log_success(f"AFL++ harness {harness_index} for {api_name} saved to {afl_filepath}")
                    else:
                        log_warning(f"Failed to convert harness {harness_index} for {api_name} to AFL++ format")
                    
                    # Clean up temporary files
                    try:
                        os.remove(temp_libfuzzer_filepath)
                        os.remove(temp_afl_filepath)
                    except:
                        pass
                    
                    # Update successful harness statistics
                    self.harness_generation_stats['successful_harnesses'] += 1
                    self.harness_generation_stats['total_harnesses_generated'] += 1
                    
                    return True
                else:
                    # Compilation failed, prepare for retry
                    log_warning(f"AFL++ compilation failed for harness {harness_index} attempt {attempt + 1}, preparing retry...")
                    
                    # Capture the compilation command and error from AFL++ version
                    try:
                        compile_cmd = compile_utils.build_compile_command(temp_afl_filepath, "/tmp/test_binary")
                        result = subprocess.run(
                            compile_cmd, 
                            capture_output=True, 
                            text=True, 
                            timeout=30
                        )
                        compile_error = result.stderr if result.stderr else "Unknown compilation error"
                            
                    except Exception as e:
                        compile_error = f"Failed to capture compilation error: {str(e)}"
                    
                    failed_code = harness_code
                    
                    # Clean up temporary files
                    try:
                        os.remove(temp_libfuzzer_filepath)
                        os.remove(temp_afl_filepath)
                    except:
                        pass
                    
                    log_error(f"Compilation error for harness {harness_index} attempt {attempt + 1}: {compile_error}")
                    
                    if attempt == max_retries - 1:
                        log_error(f"Failed to generate compilable harness {harness_index} for {api_name} after {max_retries} attempts")
                        # Update failed harness statistics
                        self.harness_generation_stats['failed_harnesses'] += 1
                        self.harness_generation_stats['total_harnesses_generated'] += 1
                        return False
                    
                    # Continue to next attempt with fix prompt
                    
            except Exception as e:
                log_error(f"Exception during harness {harness_index} generation attempt {attempt + 1} for {api_name}: {e}")
                if attempt == max_retries - 1:
                    return False
                continue
        
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
        
        # Initial prompt will be generated and saved within each harness generation attempt
        
        # Generate 3 harnesses in parallel with compilation verification
        success_count = 0
        log_info(f"Generating 3 harnesses for {api_name} with compilation verification...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit tasks for parallel execution with retry mechanism
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
                        log_success(f"Harness {harness_index} for {api_name} generated and compiled successfully")
                    else:
                        log_warning(f"Harness {harness_index} for {api_name} generation failed after all retry attempts")
                except Exception as e:
                    log_error(f"Harness {harness_index} for {api_name} generation exception: {e}")
        
        if success_count == 0:
            log_error(f"No valid harnesses generated for {api_name}")
        else:
            # 由于所有生成的harness都已经通过编译验证，跳过编译过滤步骤
            log_info(f"All {success_count} harnesses for {api_name} have passed compilation verification")
            log_info(f"Skipping compile filtering step as all harnesses are pre-verified")
            
            # 直接使用AFL++目录，无需复制
            try:
                harness_files = [f for f in os.listdir(harness_afl_dir) if f.endswith(('.c', '.cpp'))]
                
                if harness_files:
                    log_success(f"Pre-verified harnesses ready for {api_name}: {len(harness_files)} harnesses")
                    
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
                            compiled_harness_dir=harness_afl_dir,  # 直接从AFL++目录读取预验证的harness
                            executable_harness_dir=execution_filtered_dir,
                            config_parser=self.config_parser
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
                                # 从执行过滤后的文件夹读取harness，保存step3结果到coverage_log_dir
                                coverage_successful_harnesses = coverage_filter(
                                    execution_filtered_dir=execution_filtered_dir,  # 从执行过滤后的文件夹读取
                                    seeds_valid_dir=seeds_valid_dir,
                                    final_dir=coverage_filtered_dir,
                                    max_harnesses=1,  # 只选择1个最佳harness
                                    dict_file=dict_file,  # 传递dict文件路径
                                    coverage_log_dir=coverage_log_dir,  # 指定覆盖率日志保存目录
                                    config_parser=self.config_parser
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
                    log_warning(f"No pre-verified harnesses found for {api_name}")
                    
            except Exception as e:
                log_error(f"Pre-verified harness processing failed for {api_name}: {e}")
        
        return success_count > 0
    
    def _generate_cost_report(self, library_output_dir: str):
        """生成成本报告并保存到文件"""
        try:
            # Get LLM cost information
            llm_cost_info = None
            if self.llm_client:
                llm_cost_info = self.llm_client.get_total_cost()
            
            # Generate comprehensive cost report
            cost_report = {
                "harness_generation_summary": {
                    "total_apis_processed": self.harness_generation_stats['total_apis_processed'],
                    "total_harnesses_generated": self.harness_generation_stats['total_harnesses_generated'],
                    "successful_harnesses": self.harness_generation_stats['successful_harnesses'],
                    "failed_harnesses": self.harness_generation_stats['failed_harnesses'],
                    "success_rate": (self.harness_generation_stats['successful_harnesses'] / 
                                   max(self.harness_generation_stats['total_harnesses_generated'], 1)) * 100,
                    "total_llm_calls": self.harness_generation_stats['total_llm_calls']
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
                    "cost_per_api": (llm_cost_info.cost_usd / max(self.harness_generation_stats['total_apis_processed'], 1)) if llm_cost_info else 0.0,
                    "cost_per_harness": (llm_cost_info.cost_usd / max(self.harness_generation_stats['total_harnesses_generated'], 1)) if llm_cost_info else 0.0,
                    "cost_per_successful_harness": (llm_cost_info.cost_usd / max(self.harness_generation_stats['successful_harnesses'], 1)) if llm_cost_info else 0.0,
                    "average_tokens_per_call": (llm_cost_info.total_tokens / max(self.harness_generation_stats['total_llm_calls'], 1)) if llm_cost_info else 0.0
                }
            }
            
            # Save cost report to file
            cost_report_file = os.path.join(library_output_dir, "harness_generation_cost_report.json")
            with open(cost_report_file, 'w', encoding='utf-8') as f:
                json.dump(cost_report, f, indent=2, ensure_ascii=False)
            
            # Log cost summary
            if llm_cost_info:
                log_success(f"Harness生成成本报告:")
                log_info(f"  - 处理API数量: {self.harness_generation_stats['total_apis_processed']}")
                log_info(f"  - 生成harness数量: {self.harness_generation_stats['total_harnesses_generated']} (成功: {self.harness_generation_stats['successful_harnesses']}, 失败: {self.harness_generation_stats['failed_harnesses']})")
                log_info(f"  - LLM调用次数: {self.harness_generation_stats['total_llm_calls']}")
                log_info(f"  - 总token数: {llm_cost_info.total_tokens:,} (输入: {llm_cost_info.input_tokens:,}, 输出: {llm_cost_info.output_tokens:,})")
                log_info(f"  - 总成本: ${llm_cost_info.cost_usd:.4f} USD")
                log_info(f"  - 平均每个API成本: ${cost_report['cost_breakdown']['cost_per_api']:.4f} USD")
                log_info(f"  - 平均每个成功harness成本: ${cost_report['cost_breakdown']['cost_per_successful_harness']:.4f} USD")
                log_success(f"详细成本报告已保存到: {cost_report_file}")
            else:
                log_warning("LLM客户端不可用，无法生成详细成本信息")
                
        except Exception as e:
            log_error(f"生成成本报告时发生错误: {e}")