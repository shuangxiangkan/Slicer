#!/usr/bin/env python3
"""
Main entry point for the fuzzing driver generation
"""

import argparse
import sys
from library_handler import LibraryHandler
from logging import logger

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Fuzzing driver generation tool.")
    parser.add_argument("--config", type=str, required=True, help="Path to the library configuration file.")
    parser.add_argument("--type", type=str, choices=["static", "shared", "both"], default="static", 
                       help="Library type to compile: static, shared, or both (default: static)")
    
    args = parser.parse_args()
    
    logger.info(f"Using configuration file: {args.config}")
    logger.info(f"Compilation type: {args.type}")
    
    try:
        handler = LibraryHandler(args.config)
        
        success = True
        
        if args.type in ["static", "both"]:
            logger.info("Starting static library compilation...")
            if not handler.compile_static_library():
                logger.error("Failed to compile static library.")
                success = False
            else:
                logger.info("Static library compiled successfully.")
        
        if args.type in ["shared", "both"]:
            logger.info("Starting shared library compilation...")
            if not handler.compile_shared_library():
                logger.error("Failed to compile shared library.")
                success = False
            else:
                logger.info("Shared library compiled successfully.")
        
        if not success:
            logger.error("Library compilation failed. Exiting.")
            sys.exit(1)
            
        logger.info("All requested library compilations completed successfully.")
        
    except Exception as e:
        logger.error(f"Error during library compilation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()