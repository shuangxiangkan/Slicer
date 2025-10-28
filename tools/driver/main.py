#!/usr/bin/env python3
"""
Library compilation utility
"""

import sys
import time
from pathlib import Path
from library_handler import LibraryHandler
from config_parser import ConfigParser
from log import *
from utils import verify_fuzzing_environment, generate_final_summary, print_final_summary

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer

def create_repo_analyzer(config_parser: ConfigParser) -> RepoAnalyzer:
    """
    Create and initialize RepoAnalyzer instance
    
    Args:
        config_parser: Configuration parser instance
        
    Returns:
        RepoAnalyzer instance with basic analysis completed
    """
    log_info(f"Using direct parameter mode for analysis: {config_parser.get_target_library_dir()}")
    
    # Initialize analyzer (direct parameter mode)
    analyzer = RepoAnalyzer(
        library_path=config_parser.get_target_library_dir(),
        header_files=config_parser.get_headers(),
        include_files=config_parser.get_source_dirs(),
        exclude_files=config_parser.get_exclude_dirs()
    )
    
    # Execute basic analysis
    result = analyzer.analyze()
    log_info(f"Basic analysis completed, found {result['total_functions']} functions")
    
    return analyzer

def harness_generation(config_path: str, library_type: str = "static") -> bool:
    """
    Main function for harness generation
    
    Args:
        config_path: Configuration file path
        library_type: Library type ("static", "shared")
        
    Returns:
        True if harness generation is successful, False otherwise.
    """
    # Record start time
    start_time = time.time()
    
    try:
        # Parse configuration
        config_parser = ConfigParser(config_path)
        log_success("Configuration parsed successfully.")
        
        # Verify fuzzing environment
        env_ready, missing_tools = verify_fuzzing_environment()
        if not env_ready:
            log_error(f"Fuzzing environment incomplete, missing necessary tools: {', '.join(missing_tools)}")
            log_error("Please install AFL++ and ensure it is in the PATH environment variable")
            return False
        log_success("Fuzzing environment verification passed")
        
        # Get directory path through config_parser
        library_output_dir = config_parser.get_output_dir()
        
        # Create LibraryHandler instance
        handler = LibraryHandler(config_parser)
        
        # Step 1: Compile library file
        success = handler.compile_library(library_type)
        if not success:
            log_error("Library file compilation failed, terminating harness generation")    
            return False
        
        # Step 2: Create RepoAnalyzer instance (after compilation)
        analyzer = create_repo_analyzer(config_parser)
        
        # Step 3: Extract API and save to file
        api_functions = handler.get_all_apis(library_output_dir, analyzer)
        
        # Step 3: Check API function extraction result
        if not api_functions:
            log_error("No API functions found, terminating harness generation")
            return False
        
        # Step 4: Extract API comments and save result
        comments_results = handler.get_api_comments(api_functions, analyzer, library_output_dir)
        
        # Step 5: Search API documentation and save result
        documentation_results = handler.get_api_documentation(api_functions, analyzer, library_output_dir)
        
        # Step 6: Compute API usage statistics and save result
        usage_results, api_categories = handler.get_api_usage(api_functions, analyzer, library_output_dir)
        
        # Step 7: Generate API harness
        from harness_generator import HarnessGenerator
        harness_generator = HarnessGenerator(config_parser)
        harness_success = harness_generator.generate_harnesses_for_all_apis(
             api_functions,
             api_categories,
             usage_results,
             comments_results,
             documentation_results,
             library_output_dir
         )
        
        if not harness_success:
            log_warning("Harness generation过程中出现问题，但分析结果已保存")
        
        # Calculate total execution time
        end_time = time.time()
        total_time = end_time - start_time
        
        log_success("Harness generation completed successfully.")
        
        # Generate and print final summary
        summary = generate_final_summary(library_output_dir, total_time)
        print_final_summary(summary, library_output_dir)
            
        return True
        
    except Exception as e:
        log_error(f"Error during harness generation: {e}")
        
        # Calculate total execution time even on error
        end_time = time.time()
        total_time = end_time - start_time
        
        # Try to print summary even if there was an error
        try:
            summary = generate_final_summary(library_output_dir, total_time)
            print_final_summary(summary, library_output_dir)
        except:
            log_error("无法生成最终汇总报告")
        
        return False

if __name__ == "__main__":
    # Manually modify these parameters
    config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON/cJSON.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/libucl/libucl.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/mocklib/mocklib.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/libpcap/libpcap.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/zlib/zlib.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/c-ares/c-ares.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/lcms/lcms.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/magic/magic.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/pcre2/pcre2.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/openexr/openexr.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/hdf5/hdf5.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cgltf/cgltf.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/StormLib/StormLib.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/libtiff/libtiff.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/libzip/libzip.yaml"
    # config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/libical/libical.yaml"
    
    library_type = "static"  # "static", "shared"
    
    success = harness_generation(config_path, library_type)
    if not success:
        sys.exit(1)