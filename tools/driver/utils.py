#!/usr/bin/env python3
"""
Utility functions for the fuzzing driver
"""

import shutil
import subprocess
import os
import re
import json
from datetime import datetime
from typing import List, Tuple, Dict, Any


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

def save_prompt_to_file(prompt: str, library_output_dir: str, api_name: str, suffix: str = "") -> str:
    """
    Save the generated prompt to a file
    
    Args:
        prompt: Generated prompt content
        library_output_dir: Library output directory
        api_name: API name
        suffix: Optional suffix for filename (for different attempts/types)
        
    Returns:
        Saved file path
    """
    # Create API-specific directory and harness_generation_logs subdirectory
    api_dir = os.path.join(library_output_dir, api_name)
    logs_dir = os.path.join(api_dir, 'harness_generation_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Save prompt file to harness_generation_logs directory
    if suffix:
        prompt_file = os.path.join(logs_dir, f"{api_name}_prompt_{suffix}.txt")
    else:
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


def save_api_generation_log(library_output_dir: str, api_name: str, generation_data: Dict[str, Any]) -> str:
    """
    Save complete API generation log to a single JSON file
    
    Args:
        library_output_dir: Library output directory
        api_name: API name
        generation_data: Complete generation data including summary and errors
        
    Returns:
        Saved file path
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create API-specific directory and harness_generation_logs subdirectory
    api_dir = os.path.join(library_output_dir, api_name)
    logs_dir = os.path.join(api_dir, 'harness_generation_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create complete log data
    log_data = {
        "timestamp": timestamp,
        "api_name": api_name,
        "summary": generation_data.get("summary", {}),
        "harness_details": generation_data.get("harness_details", [])
    }
    
    # Save to single JSON file
    log_file = os.path.join(logs_dir, f"{api_name}_generation_log.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    return log_file


def generate_final_summary(library_output_dir: str, total_time_seconds: float = None) -> Dict[str, Any]:
    """
    Generate a comprehensive summary of the entire fuzzing harness generation process
    
    Args:
        library_output_dir: Path to the library output directory
        total_time_seconds: Total execution time in seconds (optional)
        
    Returns:
        Dictionary containing comprehensive summary statistics
    """
    summary = {
        "execution_info": {},
        "llm_usage": {},
        "harness_generation": {},
        "compilation_results": {},
        "execution_results": {},
        "coverage_results": {},
        "api_breakdown": {}
    }
    
    # Add timing information if provided
    if total_time_seconds is not None:
        hours = int(total_time_seconds // 3600)
        minutes = int((total_time_seconds % 3600) // 60)
        seconds = int(total_time_seconds % 60)
        summary["execution_info"] = {
            "total_time_seconds": total_time_seconds,
            "total_time_formatted": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 1. Read global harness generation cost report
    cost_report_path = os.path.join(library_output_dir, "harness_generation_cost_report.json")
    if os.path.exists(cost_report_path):
        with open(cost_report_path, 'r', encoding='utf-8') as f:
            cost_data = json.load(f)
            
        summary["llm_usage"] = cost_data.get("llm_cost_details", {})
        summary["harness_generation"] = cost_data.get("harness_generation_summary", {})
    
    # 2. Collect API-level statistics
    api_dirs = [d for d in os.listdir(library_output_dir) 
                if os.path.isdir(os.path.join(library_output_dir, d)) 
                and not d.startswith('final_harness')]
    
    # Initialize detailed harness generation statistics
    detailed_generation_stats = {
        "total_apis_processed": 0,
        "total_harnesses_attempted": 0,
        "successful_harnesses": 0,
        "failed_harnesses": 0,
        "total_llm_calls": 0,
        "total_fix_attempts": 0,
        "compilation_errors": [],  # List of harnesses with compilation errors
        "apis_with_errors": [],   # List of APIs that had compilation errors
        "harnesses_with_fixes": []  # List of harnesses that required fixes
    }
    
    compilation_stats = {
        "total_harnesses": 0,
        "compilation_success": 0,
        "compilation_failed": 0,
        "failed_harnesses": [],  # List of specific failed harnesses
        "failed_apis": []
    }
    
    execution_stats = {
        "total_harnesses": 0,
        "execution_success": 0,
        "execution_failed": 0,
        "crashed_harnesses": 0,
        "timeout_harnesses": 0,
        "failed_harnesses": [],  # List of specific failed harnesses
        "crashed_harness_list": [],  # List of specific crashed harnesses
        "timeout_harness_list": [],  # List of specific timeout harnesses
        "failed_apis": []
    }
    
    coverage_stats = {
        "total_harnesses_fuzzed": 0,
        "harnesses_with_crashes": 0,
        "total_unique_crashes": 0,
        "crashed_harnesses": [],  # List of specific harnesses with crashes
        "apis_with_crashes": []
    }
    
    api_breakdown = {}
    
    for api_name in api_dirs:
        api_dir = os.path.join(library_output_dir, api_name)
        api_stats = {
            "harness_generation": {},
            "compilation": {},
            "execution": {},
            "coverage": {}
        }
        
        # Read API-level generation log
        gen_log_path = os.path.join(api_dir, "harness_generation_logs", f"{api_name}_generation_log.json")
        if os.path.exists(gen_log_path):
            with open(gen_log_path, 'r', encoding='utf-8') as f:
                gen_data = json.load(f)
                api_stats["harness_generation"] = gen_data.get("summary", {})
                
                # Aggregate detailed generation statistics
                summary = gen_data.get("summary", {})
                detailed_generation_stats["total_apis_processed"] += 1
                detailed_generation_stats["total_harnesses_attempted"] += summary.get("total_harnesses_attempted", 0)
                detailed_generation_stats["successful_harnesses"] += summary.get("successful_harnesses", 0)
                detailed_generation_stats["failed_harnesses"] += summary.get("failed_harnesses", 0)
                detailed_generation_stats["total_llm_calls"] += summary.get("total_llm_calls", 0)
                detailed_generation_stats["total_fix_attempts"] += summary.get("total_fix_attempts", 0)
                
                # Analyze harness details for compilation errors and fixes
                harness_details = gen_data.get("harness_details", [])
                api_has_errors = False
                
                for harness_detail in harness_details:
                    harness_index = harness_detail.get("harness_index", 0)
                    harness_name = f"{api_name}_harness_{harness_index}.c"
                    harness_full_name = f"{api_name}/{harness_name}"
                    
                    attempts = harness_detail.get("attempts", [])
                    has_compilation_error = False
                    has_fixes = len(attempts) > 1
                    
                    # Check for compilation errors in any attempt
                    for attempt in attempts:
                        if attempt.get("error_type") == "compilation_error":
                            has_compilation_error = True
                            api_has_errors = True
                            break
                    
                    if has_compilation_error:
                        detailed_generation_stats["compilation_errors"].append(harness_full_name)
                    
                    if has_fixes:
                        detailed_generation_stats["harnesses_with_fixes"].append(harness_full_name)
                
                if api_has_errors:
                    detailed_generation_stats["apis_with_errors"].append(api_name)
        
        # Read execution statistics and detailed results
        exec_stats_path = os.path.join(api_dir, "harness_execution_logs", "step2_execution_stats.json")
        exec_results_path = os.path.join(api_dir, "harness_execution_logs", "step2_execution_results.json")
        
        if os.path.exists(exec_stats_path):
            with open(exec_stats_path, 'r', encoding='utf-8') as f:
                exec_data = json.load(f)
                api_stats["execution"] = exec_data
                
                # Update global execution stats
                execution_stats["total_harnesses"] += exec_data.get("total_harnesses", 0)
                execution_stats["execution_success"] += exec_data.get("execution_success", 0)
                execution_stats["execution_failed"] += exec_data.get("execution_failed", 0)
                execution_stats["crashed_harnesses"] += len(exec_data.get("crashed_harnesses", []))
                execution_stats["timeout_harnesses"] += len(exec_data.get("timeout_harnesses", []))
                
                if exec_data.get("execution_failed", 0) > 0:
                    execution_stats["failed_apis"].append(api_name)
        
        # Read detailed execution results for specific harness information
        if os.path.exists(exec_results_path):
            with open(exec_results_path, 'r', encoding='utf-8') as f:
                exec_results = json.load(f)
                
                for result in exec_results:
                    harness_name = result.get("harness", "")
                    harness_full_name = f"{api_name}/{harness_name}"
                    
                    # Check for execution failures
                    if not result.get("execution_success", True):
                        execution_stats["failed_harnesses"].append(harness_full_name)
                    
                    # Check for crashes
                    if result.get("crashed", False):
                        execution_stats["crashed_harness_list"].append(harness_full_name)
                    
                    # Check for timeouts
                    if result.get("timeout", False):
                        execution_stats["timeout_harness_list"].append(harness_full_name)
        
        # Read coverage statistics and detailed analysis
        coverage_stats_path = os.path.join(api_dir, "harness_coverage_logs", "step3_coverage_stats.json")
        coverage_analysis_path = os.path.join(api_dir, "harness_coverage_logs", "step3_coverage_analysis.json")
        
        if os.path.exists(coverage_stats_path):
            with open(coverage_stats_path, 'r', encoding='utf-8') as f:
                cov_data = json.load(f)
                api_stats["coverage"] = cov_data
                
                # Update global coverage stats
                coverage_stats["total_harnesses_fuzzed"] += cov_data.get("total_harnesses", 0)
                
                # Count crashes from coverage analysis
                total_crashes = 0
                has_crashes = False
                for analysis in cov_data.get("coverage_analysis", []):
                    crashes = analysis.get("unique_crashes", 0)
                    total_crashes += crashes
                    if crashes > 0:
                        has_crashes = True
                
                coverage_stats["total_unique_crashes"] += total_crashes
                if has_crashes:
                    coverage_stats["harnesses_with_crashes"] += 1
                    coverage_stats["apis_with_crashes"].append(api_name)
        
        # Read detailed coverage analysis for specific harness crash information
        if os.path.exists(coverage_analysis_path):
            with open(coverage_analysis_path, 'r', encoding='utf-8') as f:
                coverage_analysis = json.load(f)
                
                for analysis in coverage_analysis:
                    harness_name = analysis.get("harness", "")
                    unique_crashes = analysis.get("unique_crashes", 0)
                    
                    if unique_crashes > 0:
                        harness_full_name = f"{api_name}/{harness_name}"
                        coverage_stats["crashed_harnesses"].append({
                            "harness": harness_full_name,
                            "unique_crashes": unique_crashes
                        })
        
        # Infer compilation statistics from directory structure
        harness_dir = os.path.join(api_dir, "harness")
        exec_filtered_dir = os.path.join(api_dir, "harness_execution_filtered")
        
        if os.path.exists(harness_dir):
            all_harnesses = [f for f in os.listdir(harness_dir) if f.endswith('.c')]
            total_harnesses = len(all_harnesses)
            compilation_stats["total_harnesses"] += total_harnesses
            
            if os.path.exists(exec_filtered_dir):
                successful_harnesses_files = [f for f in os.listdir(exec_filtered_dir) if f.endswith('.c')]
                successful_harnesses = len(successful_harnesses_files)
                failed_harnesses = total_harnesses - successful_harnesses
                
                compilation_stats["compilation_success"] += successful_harnesses
                compilation_stats["compilation_failed"] += failed_harnesses
                
                # Identify specific failed harnesses
                successful_set = set(successful_harnesses_files)
                for harness_file in all_harnesses:
                    if harness_file not in successful_set:
                        harness_full_name = f"{api_name}/{harness_file}"
                        compilation_stats["failed_harnesses"].append(harness_full_name)
                
                api_stats["compilation"] = {
                    "total_harnesses": total_harnesses,
                    "compilation_success": successful_harnesses,
                    "compilation_failed": failed_harnesses
                }
                
                if failed_harnesses > 0:
                    compilation_stats["failed_apis"].append(api_name)
        
        api_breakdown[api_name] = api_stats
    
    # Update harness_generation with detailed statistics if we have API-level data
    if detailed_generation_stats["total_apis_processed"] > 0:
        # Merge with existing global statistics if available
        existing_generation = summary.get("harness_generation", {})
        
        # Calculate success rate
        total_attempted = detailed_generation_stats["total_harnesses_attempted"]
        success_rate = (detailed_generation_stats["successful_harnesses"] / max(total_attempted, 1)) * 100
        
        summary["harness_generation"] = {
            **existing_generation,  # Keep existing global stats (like cost info)
            "total_apis_processed": detailed_generation_stats["total_apis_processed"],
            "total_harnesses_attempted": total_attempted,
            "successful_harnesses": detailed_generation_stats["successful_harnesses"],
            "failed_harnesses": detailed_generation_stats["failed_harnesses"],
            "success_rate": success_rate,
            "total_llm_calls": detailed_generation_stats["total_llm_calls"],
            "total_fix_attempts": detailed_generation_stats["total_fix_attempts"],
            "compilation_errors": detailed_generation_stats["compilation_errors"],
            "apis_with_errors": detailed_generation_stats["apis_with_errors"],
            "harnesses_with_fixes": detailed_generation_stats["harnesses_with_fixes"]
        }
    
    summary["compilation_results"] = compilation_stats
    summary["execution_results"] = execution_stats
    summary["coverage_results"] = coverage_stats
    summary["api_breakdown"] = api_breakdown
    
    return summary


def print_final_summary(summary: Dict[str, Any], library_output_dir: str = None) -> None:
    """
    Print a formatted summary of the fuzzing harness generation process and save to file
    
    Args:
        summary: Summary dictionary from generate_final_summary
        library_output_dir: Directory to save the summary file
    """
    # Generate the formatted summary text
    summary_text = _format_summary_text(summary)
    
    # Print to console
    print(summary_text)
    
    # Save to file if library_output_dir is provided
    if library_output_dir:
        try:
            summary_file_path = os.path.join(library_output_dir, "final_summary.txt")
            with open(summary_file_path, 'w', encoding='utf-8') as f:
                f.write(summary_text)
            print(f"\n📄 Summary saved to: {summary_file_path}")
        except Exception as e:
            print(f"\n⚠️  Warning: Failed to save summary to file: {e}")


def _format_summary_text(summary: Dict[str, Any]) -> str:
    """
    Format the summary data into a readable text format
    
    Args:
        summary: Summary dictionary from generate_final_summary
        
    Returns:
        Formatted summary text
    """
    lines = []
    lines.append("="*80)
    lines.append("🎯 FUZZING HARNESS GENERATION - FINAL SUMMARY")
    lines.append("="*80)
    
    # Execution info
    if summary.get("execution_info"):
        exec_info = summary["execution_info"]
        lines.append(f"\n⏱️  EXECUTION TIME:")
        lines.append(f"   Total Time: {exec_info.get('total_time_formatted', 'N/A')}")
        lines.append(f"   Completed: {exec_info.get('timestamp', 'N/A')}")
    
    # LLM Usage
    if summary.get("llm_usage"):
        llm = summary["llm_usage"]
        lines.append(f"\n🤖 LLM USAGE & COST:")
        lines.append(f"   Provider: {llm.get('provider', 'N/A')}")
        lines.append(f"   Model: {llm.get('model', 'N/A')}")
        lines.append(f"   Total Requests: {llm.get('total_requests', 0)}")
        lines.append(f"   Input Tokens: {llm.get('input_tokens', 0):,}")
        lines.append(f"   Output Tokens: {llm.get('output_tokens', 0):,}")
        lines.append(f"   Total Tokens: {llm.get('total_tokens', 0):,}")
        lines.append(f"   💰 Total Cost: ${llm.get('total_cost_usd', 0):.4f} USD")
    
    # Harness Generation
    if summary.get("harness_generation"):
        gen = summary["harness_generation"]
        lines.append(f"\n📝 HARNESS GENERATION:")
        lines.append(f"   APIs Processed: {gen.get('total_apis_processed', 0)}")
        
        # Use new detailed fields if available, fallback to old fields
        total_attempted = gen.get('total_harnesses_attempted', gen.get('total_harnesses_generated', 0))
        successful = gen.get('successful_harnesses', 0)
        failed = gen.get('failed_harnesses', 0)
        
        lines.append(f"   Harnesses Attempted: {total_attempted}")
        lines.append(f"   ✅ Successful: {successful}")
        lines.append(f"   ❌ Failed: {failed}")
        lines.append(f"   LLM Calls: {gen.get('total_llm_calls', 0)}")
        lines.append(f"   Fix Attempts: {gen.get('total_fix_attempts', 0)}")
        lines.append(f"   Success Rate: {gen.get('success_rate', 0):.1f}%")
        
        # Show compilation errors during generation
        compilation_errors = gen.get('compilation_errors', [])
        if compilation_errors:
            lines.append(f"   Compilation Errors During Generation:")
            for harness in compilation_errors:
                lines.append(f"     - {harness}")
        
        # Show harnesses that required fixes
        harnesses_with_fixes = gen.get('harnesses_with_fixes', [])
        if harnesses_with_fixes:
            lines.append(f"   Harnesses Requiring Fixes:")
            for harness in harnesses_with_fixes:
                lines.append(f"     - {harness}")
        
        # Show APIs with errors
        apis_with_errors = gen.get('apis_with_errors', [])
        if apis_with_errors:
            lines.append(f"   APIs with Generation Errors: {', '.join(apis_with_errors)}")
    
    # Compilation Results
    if summary.get("compilation_results"):
        comp = summary["compilation_results"]
        lines.append(f"\n🔨 COMPILATION RESULTS:")
        lines.append(f"   Total Harnesses: {comp.get('total_harnesses', 0)}")
        lines.append(f"   ✅ Compilation Success: {comp.get('compilation_success', 0)}")
        lines.append(f"   ❌ Compilation Failed: {comp.get('compilation_failed', 0)}")
        
        # Show specific failed harnesses
        failed_harnesses = comp.get('failed_harnesses', [])
        if failed_harnesses:
            lines.append(f"   Failed Harnesses:")
            for harness in failed_harnesses:
                lines.append(f"     - {harness}")
        
        if comp.get('failed_apis'):
            lines.append(f"   Failed APIs: {', '.join(comp['failed_apis'])}")
    
    # Execution Results
    if summary.get("execution_results"):
        exec_res = summary["execution_results"]
        lines.append(f"\n🚀 EXECUTION RESULTS:")
        lines.append(f"   Total Harnesses: {exec_res.get('total_harnesses', 0)}")
        lines.append(f"   ✅ Execution Success: {exec_res.get('execution_success', 0)}")
        lines.append(f"   ❌ Execution Failed: {exec_res.get('execution_failed', 0)}")
        lines.append(f"   💥 Crashed: {exec_res.get('crashed_harnesses', 0)}")
        lines.append(f"   ⏰ Timeout: {exec_res.get('timeout_harnesses', 0)}")
        
        # Show specific failed harnesses
        failed_harnesses = exec_res.get('failed_harnesses', [])
        if failed_harnesses:
            lines.append(f"   Failed Harnesses:")
            for harness in failed_harnesses:
                lines.append(f"     - {harness}")
        
        # Show specific crashed harnesses
        crashed_harnesses = exec_res.get('crashed_harness_list', [])
        if crashed_harnesses:
            lines.append(f"   Crashed Harnesses:")
            for harness in crashed_harnesses:
                lines.append(f"     - {harness}")
        
        # Show specific timeout harnesses
        timeout_harnesses = exec_res.get('timeout_harness_list', [])
        if timeout_harnesses:
            lines.append(f"   Timeout Harnesses:")
            for harness in timeout_harnesses:
                lines.append(f"     - {harness}")
        
        if exec_res.get('failed_apis'):
            lines.append(f"   Failed APIs: {', '.join(exec_res['failed_apis'])}")
    
    # Coverage Results
    if summary.get("coverage_results"):
        cov = summary["coverage_results"]
        lines.append(f"\n📊 COVERAGE & FUZZING RESULTS:")
        lines.append(f"   Harnesses Fuzzed: {cov.get('total_harnesses_fuzzed', 0)}")
        lines.append(f"   💥 Harnesses with Crashes: {cov.get('harnesses_with_crashes', 0)}")
        lines.append(f"   🐛 Total Unique Crashes: {cov.get('total_unique_crashes', 0)}")
        
        # Show specific crashed harnesses with crash counts
        crashed_harnesses = cov.get('crashed_harnesses', [])
        if crashed_harnesses:
            lines.append(f"   Crashed Harnesses:")
            for crash_info in crashed_harnesses:
                harness = crash_info.get('harness', 'Unknown')
                crashes = crash_info.get('unique_crashes', 0)
                lines.append(f"     - {harness} ({crashes} unique crashes)")
        
        if cov.get('apis_with_crashes'):
            lines.append(f"   APIs with Crashes: {', '.join(cov['apis_with_crashes'])}")
    
    lines.append("\n" + "="*80)
    
    return "\n".join(lines)


if __name__ == "__main__":
    ready, missing = verify_fuzzing_environment()
    if ready:
        print("✓ Fuzzing environment ready!")
    else:
        print(f"✗ Missing necessary tools: {', '.join(missing)}")
        print("Please install AFL++ and ensure it is in the PATH environment variable")