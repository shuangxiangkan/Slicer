#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prompt Template Generator
For generating LLM prompts for Libfuzzer fuzz harness
"""

from typing import Dict, List, Any


class PromptGenerator:
    """Generate prompt templates for LLM"""
    
    def __init__(self, config_parser):
        self.config_parser = config_parser
        self.library_name = config_parser.get_library_name()
        self.include_headers = config_parser.get_include_headers()
        
    def generate_fuzz_harness_prompt(self, api_info: Dict[str, Any]) -> str:
        """Generate prompt for creating Libfuzzer fuzz harness"""
        
        api_name = api_info.get('api_name', '')
        signature = api_info.get('signature', '')
        comments = api_info.get('comments', '')
        documentation = api_info.get('documentation', '')
        usage_examples = api_info.get('top_3_usage', [])
        
        # Get library language information
        library_info = self.config_parser.get_library_info()
        language = library_info.get('language', 'C').upper()
        
        # Build headers section
        headers_section = self._build_headers_section()
        
        # Build examples section
        examples_section = self._build_examples_section(usage_examples)
        
        # Determine language-specific requirements
        if language == 'C++':
            language_requirements = "Please generate C++ code following C++ best practices."
            code_style = "C++"
            entry_function = "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)"
        else:
            language_requirements = "Please generate C code following C best practices."
            code_style = "C"
            entry_function = "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)"
        
        prompt = f"""You are a professional {code_style} fuzzing expert. Please generate a high-quality Libfuzzer fuzz harness for the API function {api_name} in the {self.library_name} library.

## Target API Information

**Function Signature**: {signature}

**Include Headers**:
{headers_section}

**Function Description**:
{comments}

**Documentation**:
{documentation}

{examples_section}

## Requirements

{language_requirements}

Please use the standard Libfuzzer entry function: `{entry_function}` to generate 1 complete {code_style} fuzz harness, including all necessary header files, function implementations, and error handling. The code should be directly usable for Libfuzzer fuzzing tests.
"""
        
        return prompt
    
    def _build_headers_section(self) -> str:
        """Build headers include section"""
        if not self.include_headers:
            return "   - Include necessary system headers and library headers"
        
        headers_list = []
        for header in self.include_headers:
            headers_list.append(f"   - #include <{header}>")
        
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
    
    def generate_fix_harness_prompt(self, api_info: Dict[str, Any], failed_code: str, compile_error: str) -> str:
        """Generate prompt for fixing compilation errors in fuzz harness"""
        
        api_name = api_info.get('api_name', '')
        signature = api_info.get('signature', '')
        comments = api_info.get('comments', '')
        documentation = api_info.get('documentation', '')
        usage_examples = api_info.get('top_3_usage', [])
        
        # Get library language information
        library_info = self.config_parser.get_library_info()
        language = library_info.get('language', 'C').upper()
        
        # Build headers section
        headers_section = self._build_headers_section()
        
        # Build examples section
        examples_section = self._build_examples_section(usage_examples)
        
        # Determine language-specific requirements
        if language == 'C++':
            language_requirements = "Please generate C++ code following C++ best practices."
            code_style = "C++"
            entry_function = "extern \"C\" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)"
        else:
            language_requirements = "Please generate C code following C best practices."
            code_style = "C"
            entry_function = "int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)"
        
        prompt = f"""You are a professional {code_style} fuzzing expert. The previous fuzz harness for API function {api_name} failed to compile. Please analyze the compilation error and generate a corrected version.

## Target API Information

**Function Signature**: {signature}

**Include Headers**:
{headers_section}

**Function Description**:
{comments}

**Documentation**:
{documentation}

{examples_section}

## Failed Code

The following code failed to compile:

```{code_style.lower()}
{failed_code}
```

## Compilation Error

```
{compile_error}
```

## Requirements

{language_requirements}

Please analyze the compilation error carefully and generate a CORRECTED {code_style} fuzz harness using the standard Libfuzzer entry function: `{entry_function}`. 

**Key points to address:**
1. Fix the specific compilation error mentioned above
2. Ensure all necessary headers are included
3. Handle any missing function declarations or definitions
4. Correct any syntax or linking issues
5. Make sure the harness is compatible with the target library

Generate ONLY the corrected complete {code_style} code that will compile successfully.
"""
        
        return prompt