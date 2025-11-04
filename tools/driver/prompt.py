#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt Template Generator
For generating LLM prompts for Libfuzzer fuzz harness
"""

import os
from typing import Dict, List, Any


class PromptGenerator:
    """Generate prompt templates for LLM"""
    
    def __init__(self, config_parser, library_output_dir: str = None):
        self.config_parser = config_parser
        self.library_name = config_parser.get_library_name()
        self.include_headers = config_parser.get_include_headers()
        self.library_output_dir = library_output_dir
        
        # Set prompts directory path
        self.prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    
    def _load_prompt_template(self, template_name: str) -> str:
        """Load prompt template from file
        
        Args:
            template_name: Name of the template file (without .txt extension)
            
        Returns:
            Template content as string
        """
        template_path = os.path.join(self.prompts_dir, f"{template_name}.txt")
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        except Exception as e:
            raise Exception(f"Error loading prompt template {template_name}: {str(e)}")
        
    def generate_fuzz_harness_prompt(self, api_info: Dict[str, Any]) -> str:
        """Generate prompt for creating Libfuzzer fuzz harness"""
        
        api_name = api_info.get('api_name', '')
        signature = api_info.get('signature', '')
        comments = api_info.get('comments', '')
        documentation = api_info.get('documentation', '')
        usage_examples = api_info.get('top_n_usage', [])
        api_category = api_info.get('api_category', 'unknown')
        dependency_context = api_info.get('dependency_context', {})
        
        # Get library language information
        library_info = self.config_parser.get_library_info()
        language = library_info.get('language', 'C').upper()
        
        # Build headers section
        headers_section = self._build_headers_section()
        
        # Build examples and reference sections based on API category
        examples_section, reference_section = self._build_examples_and_references_section(
            usage_examples, dependency_context, api_category
        )
        
        # Select language-specific template
        if language == 'C++':
            template_name = 'fuzz_harness_generation_cpp'
        else:
            template_name = 'fuzz_harness_generation_c'
        
        # Load template and fill in variables
        template = self._load_prompt_template(template_name)
        prompt = template.format(
            api_name=api_name,
            library_name=self.library_name,
            signature=signature,
            headers_section=headers_section,
            comments=comments,
            documentation=documentation,
            examples_section=examples_section,
            reference_section=reference_section
        )
        
        return prompt
    
    def generate_api_documentation_extraction_prompt(self, document_content: str, api_functions: List[str]) -> str:
        """Generate prompt for extracting API documentation and usage from documents"""
        
        # Load template and fill in variables
        template = self._load_prompt_template('api_documentation_extraction')
        prompt = template.format(
            document_content=document_content
        )
        
        return prompt
        
    def _build_headers_section(self) -> str:
        """Build headers include section"""
        if not self.include_headers:
            return "   - Include necessary system headers and library headers"
        
        headers_list = []
        for header in self.include_headers:
            # Remove any path prefix from header names
            # e.g., "include/ucl.h" -> "ucl.h"
            # e.g., "src/ucl.h" -> "ucl.h"
            clean_header = header.split('/')[-1] if '/' in header else header
            headers_list.append(f"   - #include <{clean_header}>")
        
        return "\n".join(headers_list)
    
    def _build_examples_section(self, usage_examples: List[Dict[str, Any]]) -> str:
        """Build usage examples section"""
        if not usage_examples:
            return "## Usage Examples\n\nNo usage examples available."
        
        examples_text = "## Usage Examples\n\nHere are some usage examples of this API that can be used as reference for generating harness:\n\n"
        
        for i, example in enumerate(usage_examples[:3], 1):
            code = example.get('code', '').strip()
            if code:
                examples_text += f"**Example {i}**:\n```c\n{code}\n```\n\n"
        
        return examples_text
    
    def _build_examples_and_references_section(self, usage_examples: List[Dict[str, Any]], 
                                             dependency_context: Dict[str, Any], 
                                             api_category: str) -> tuple:
        """
        根据API类型智能构建usage examples和reference harnesses部分
        
        Args:
            usage_examples: API的usage示例列表
            dependency_context: 依赖上下文，包含相似API信息
            api_category: API类型 (fuzz/test_demo/other_usage/no_usage)
            
        Returns:
            tuple: (examples_section, reference_section)
        """
        similar_apis = dependency_context.get('similar_apis', [])
        
        # 根据API类型决定策略
        if api_category in ['fuzz', 'test_demo']:
            # 策略1: fuzz/test类API - 直接使用前3个usage examples
            examples_section = self._build_examples_section(usage_examples[:3])
            reference_section = ""
            
        elif api_category == 'other_usage' and usage_examples:
            # 策略2: other_usage类API且有usage - 前2个usage + 1个相似API harness
            examples_section = self._build_examples_section(usage_examples[:2])
            reference_section = self._build_reference_harnesses_section(similar_apis[:1])
            
        else:
            # 策略3: 无usage的API或other_usage但无usage - 使用前3个相似API harness
            examples_section = "## Usage Examples\n\nNo usage examples available for this API."
            reference_section = self._build_reference_harnesses_section(similar_apis[:3])
        
        return examples_section, reference_section
    
    def _build_reference_harnesses_section(self, similar_apis: List[Dict[str, Any]]) -> str:
        """构建相似API harness参考部分"""
        if not similar_apis:
            return ""
        
        # 过滤出有harness文件的相似API
        apis_with_harness = [api for api in similar_apis if api.get('has_reference', False)]
        
        if not apis_with_harness:
            return ""
        
        reference_text = "## Reference Harnesses from Similar APIs\n\n"
        reference_text += "Here are harness implementations from similar APIs that can be used as reference:\n\n"
        
        for i, api_info in enumerate(apis_with_harness, 1):
            api_name = api_info.get('api_name', '')
            similarity_score = api_info.get('similarity_score', 0.0)
            
            # 尝试读取harness文件内容
            harness_content = self._read_reference_harness_content(api_name)
            
            if harness_content:
                reference_text += f"**Reference {i} - {api_name}** (Similarity: {similarity_score:.3f}):\n"
                reference_text += f"```c\n{harness_content}\n```\n\n"
        
        return reference_text
    
    def _read_reference_harness_content(self, api_name: str) -> str:
        """读取参考harness文件内容"""
        if not self.library_output_dir:
            return f"// Reference harness for {api_name}\n// Content will be loaded from generated harness file"
        
        # 查找harness文件路径
        harness_file_path = self._find_reference_harness_file(api_name)
        
        if harness_file_path and os.path.exists(harness_file_path):
            try:
                with open(harness_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    # 限制内容长度，避免prompt过长
                    if len(content) > 2000:
                        content = content[:2000] + "\n// ... (content truncated for brevity)"
                    return content
            except Exception as e:
                return f"// Error reading harness file for {api_name}: {str(e)}"
        
        return f"// Reference harness for {api_name}\n// Harness file not found"
    
    def _find_reference_harness_file(self, api_name: str) -> str:
        """查找指定API的已生成harness文件"""
        if not self.library_output_dir:
            return None
            
        # 检查final_harness_libfuzzer目录（优先）
        final_libfuzzer_dir = os.path.join(self.library_output_dir, "final_harness_libfuzzer")
        if os.path.exists(final_libfuzzer_dir):
            for file in os.listdir(final_libfuzzer_dir):
                if file.startswith(f"{api_name}_harness") and file.endswith(('.c', '.cpp')):
                    harness_path = os.path.join(final_libfuzzer_dir, file)
                    if os.path.isfile(harness_path):
                        return harness_path
        
        # 检查harnesses/libfuzzer目录
        libfuzzer_dir = os.path.join(self.library_output_dir, "harnesses", "libfuzzer")
        if os.path.exists(libfuzzer_dir):
            for file in os.listdir(libfuzzer_dir):
                if file.startswith(f"{api_name}_harness") and file.endswith(('.c', '.cpp')):
                    harness_path = os.path.join(libfuzzer_dir, file)
                    if os.path.isfile(harness_path):
                        return harness_path
        
        # 检查harnesses/afl目录
        afl_dir = os.path.join(self.library_output_dir, "harnesses", "afl")
        if os.path.exists(afl_dir):
            for file in os.listdir(afl_dir):
                if file.startswith(f"{api_name}_harness") and file.endswith(('.c', '.cpp')):
                    harness_path = os.path.join(afl_dir, file)
                    if os.path.isfile(harness_path):
                        return harness_path
        
        return None

    def generate_fix_harness_prompt(self, api_info: Dict[str, Any], failed_code: str, compile_error: str) -> str:
        """Generate prompt for fixing compilation errors in fuzz harness"""
        
        api_name = api_info.get('api_name', '')
        signature = api_info.get('signature', '')
        comments = api_info.get('comments', '')
        documentation = api_info.get('documentation', '')
        usage_examples = api_info.get('top_n_usage', [])
        api_category = api_info.get('api_category', 'unknown')
        dependency_context = api_info.get('dependency_context', {})
        
        # Get library language information
        library_info = self.config_parser.get_library_info()
        language = library_info.get('language', 'C').upper()
        
        # Build headers section
        headers_section = self._build_headers_section()
        
        # Build examples and reference sections based on API category
        examples_section, reference_section = self._build_examples_and_references_section(
            usage_examples, dependency_context, api_category
        )
        
        # Select language-specific template
        if language == 'C++':
            template_name = 'fix_harness_compilation_cpp'
        else:
            template_name = 'fix_harness_compilation_c'
        
        # Load template and fill in variables
        template = self._load_prompt_template(template_name)
        prompt = template.format(
            api_name=api_name,
            signature=signature,
            headers_section=headers_section,
            comments=comments,
            documentation=documentation,
            examples_section=examples_section,
            reference_section=reference_section,
            failed_code=failed_code,
            compile_error=compile_error
        )
        
        return prompt