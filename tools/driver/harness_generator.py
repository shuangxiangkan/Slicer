#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness Generator Module

为API函数生成按优先级排序的完整信息
"""

import os
import json
from typing import Dict, List, Any
from log import log_info, log_success, log_warning, log_error
from utils import save_prompt_to_file


class HarnessGenerator:
    """API信息生成器类"""
    
    def __init__(self, config_parser):
        self.config_parser = config_parser
        from prompt import PromptGenerator
        self.prompt_generator = PromptGenerator(config_parser)
    
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
            
            for priority in priority_order:
                api_list = prioritized_apis.get(priority, [])
                if not api_list:
                    continue
                    
                log_info(f"处理 {priority} 类型API ({len(api_list)}个)...")
                
                for api_func in api_list:
                    api_info = self._collect_api_info(
                        api_func,
                        usage_results,
                        similarity_results,
                        comments_results,
                        documentation_results,
                        priority
                    )
                    api_info_list.append(api_info)
                    
                    # Generate prompt for each API and save to file
                    prompt = self.generate_fuzz_harness_prompt(api_info)
                    api_name = api_info.get('api_name', 'unknown_api')
                    prompt_file = save_prompt_to_file(prompt, library_output_dir, api_name)
                    log_info(f"Generated prompt for {api_name} saved to {prompt_file}")
            
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