#!/usr/bin/env python3
"""
Utility functions for the fuzzing driver
"""

import shutil
import subprocess
import os
import re
from typing import List, Tuple


def verify_fuzzing_environment() -> Tuple[bool, List[str]]:
    """
    Verify if all required fuzzing tools are available in the environment.
    
    Returns:
        Tuple of (all_tools_available, missing_tools_list)
    """
    # required fuzzing tools
    required_tools = [
        'afl-clang-fast',  
        'afl-clang-fast++',  
        'afl-showmap',       
        'afl-fuzz'           
    ]
    
    missing_tools = []
    
    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    return len(missing_tools) == 0, missing_tools

def check_afl_instrumentation(library_path: str) -> Tuple[bool, str]:
    """
    Check if the compiled library file has been successfully instrumented by AFL++.
    
    Args:
        library_path: Path to the library file (.a or .so file)
        
    Returns:
        Tuple of (is_instrumented, message)
    """
    if not os.path.exists(library_path):
        return False, f"Library file does not exist: {library_path}"
    
    try:
        # Use strings command to check the strings in the binary file
        result = subprocess.run(
            ['strings', library_path], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode != 0:
            return False, f"Cannot read library file content: {library_path}"
        
        output = result.stdout.lower()
        
        # Check AFL++ instrumentation feature strings
        afl_signatures = [
            '__afl_',           # AFL++ function prefix
            'afl_area_ptr',     # AFL++ shared memory pointer
            'afl_prev_loc',     # AFL++ previous location
            '__sanitizer_cov_trace_pc_guard',  # Coverage tracing
            'llvm_gcov_',       # LLVM coverage
        ]
        
        found_signatures = []
        for signature in afl_signatures:
            if signature in output:
                found_signatures.append(signature)
        
        if found_signatures:
            return True, f"Detected AFL++ instrumentation features: {', '.join(found_signatures)}"
        else:
            return False, "No AFL++ instrumentation features detected, possibly compiled without afl-clang-fast"
            
    except subprocess.TimeoutExpired:
        return False, f"Check timeout: {library_path}"
    except Exception as e:
        return False, f"Check error: {str(e)}"

def save_prompt_to_file(prompt: str, library_output_dir: str, api_name: str) -> str:
    """
    Save the generated prompt to a file
    
    Args:
        prompt: Generated prompt content
        library_output_dir: Library output directory
        api_name: API name
        
    Returns:
        Saved file path
    """
    # Create API-specific directory and harness_generation_logs subdirectory
    api_dir = os.path.join(library_output_dir, api_name)
    logs_dir = os.path.join(api_dir, 'harness_generation_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Save prompt file to harness_generation_logs directory
    prompt_file = os.path.join(logs_dir, f"{api_name}_prompt.txt")
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    return prompt_file

def save_llm_response_to_file(response: str, library_output_dir: str, api_name: str, response_index: int = None) -> str:
    """
    Save the LLM response to a file
    
    Args:
        response: LLM response content
        library_output_dir: Library output directory
        api_name: API name
        response_index: Response index (optional, for multiple responses)
        
    Returns:
        Saved file path
    """
    # Create API-specific directory and harness_generation_logs subdirectory
    api_dir = os.path.join(library_output_dir, api_name)
    logs_dir = os.path.join(api_dir, 'harness_generation_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Save response file to harness_generation_logs directory
    if response_index is not None:
        response_file = os.path.join(logs_dir, f"{api_name}_response_{response_index}.txt")
    else:
        response_file = os.path.join(logs_dir, f"{api_name}_response.txt")
    
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write(response)
    
    return response_file

def extract_code_from_response(response: str) -> str:
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

def get_file_extension(config_parser) -> str:
    """Get file extension based on library language"""
    library_info = config_parser.get_library_info()
    language = library_info.get('language', 'C').upper()
    return '.cpp' if language == 'C++' else '.c'


if __name__ == "__main__":
    ready, missing = verify_fuzzing_environment()
    if ready:
        print("✓ Fuzzing environment ready!")
    else:
        print(f"✗ Missing necessary tools: {', '.join(missing)}")
        print("Please install AFL++ and ensure it is in the PATH environment variable")