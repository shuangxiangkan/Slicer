#!/usr/bin/env python3
"""
Library handler for compiling and managing libraries.
"""

import subprocess
import os
from config_parser import ConfigParser
from logging import logger
from utils import check_afl_instrumentation

class LibraryHandler:
    """Handles library operations like compilation."""

    def __init__(self, config_path: str):
        """
        Initializes the LibraryHandler with a configuration file.

        Args:
            config_path: Path to the YAML configuration file.
        """
        self.config_parser = ConfigParser(config_path)
        self.library_name = self.config_parser.get_library_info()['name']
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.libs_dir = os.path.join(self.base_dir, "libraries")
        os.makedirs(self.libs_dir, exist_ok=True)

    def compile_static_library(self) -> bool:
        """
        Compiles the static library based on the configuration.

        Returns:
            True if compilation is successful, False otherwise.
        """
        logger.info(f"Starting static compilation for {self.library_name}...")
        
        build_command = self.config_parser.get_formatted_static_build_command()
        
        logger.info(f"Executing command in {self.libs_dir}: {build_command}")
        
        try:
            # Using shell=True because the command is a string with shell features (&&, cd)
            result = subprocess.run(build_command, shell=True, check=True, capture_output=True, text=True, cwd=self.libs_dir)
            logger.info(f"Compilation successful for {self.library_name}.")
            logger.info(f"STDOUT:\n{result.stdout}")
            logger.info("Static library compilation completed successfully.")
            
            # 检查AFL++插桩
            static_build_config = self.config_parser.get_static_build_config()
            formatted_output = self.config_parser.format_command(static_build_config['output'])
            library_path = os.path.join(self.libs_dir, formatted_output)
            
            if os.path.exists(library_path):
                if check_afl_instrumentation(library_path):
                    logger.info(f"AFL++ instrumentation verified successfully for {library_path}")
                else:
                    logger.error(f"AFL++ instrumentation verification failed for {library_path}")
                    return False
            else:
                logger.error(f"Library file not found at expected path: {library_path}")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation failed for {self.library_name}.")
            logger.error(f"Return code: {e.returncode}")
            logger.error(f"STDOUT:\n{e.stdout}")
            logger.error(f"STDERR:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during compilation: {e}")
            return False
    
    def compile_shared_library(self) -> bool:
        """
        Compiles the shared library based on the configuration.

        Returns:
            True if compilation is successful, False otherwise.
        """
        logger.info(f"Starting shared library compilation for {self.library_name}...")
        
        shared_build_config = self.config_parser.get_shared_build_config()
        if shared_build_config is None:
            logger.error(f"No shared library build configuration found for {self.library_name}")
            return False
        
        build_command = self.config_parser.get_formatted_shared_build_command()
        if build_command is None:
            logger.error(f"No shared library build command found for {self.library_name}")
            return False
        
        logger.info(f"Executing command in {self.libs_dir}: {build_command}")
        
        try:
            # Using shell=True because the command is a string with shell features (&&, cd)
            result = subprocess.run(build_command, shell=True, check=True, capture_output=True, text=True, cwd=self.libs_dir)
            logger.info(f"Shared library compilation successful for {self.library_name}.")
            logger.info(f"STDOUT:\n{result.stdout}")
            logger.info("Shared library compilation completed successfully.")
            
            # 检查AFL++插桩
            formatted_output = self.config_parser.format_command(shared_build_config['output'])
            library_path = os.path.join(self.libs_dir, formatted_output)
            
            if os.path.exists(library_path):
                if check_afl_instrumentation(library_path):
                    logger.info(f"AFL++ instrumentation verified successfully for {library_path}")
                else:
                    logger.error(f"AFL++ instrumentation verification failed for {library_path}")
                    return False
            else:
                logger.error(f"Shared library file not found at expected path: {library_path}")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Shared library compilation failed for {self.library_name}.")
            logger.error(f"Return code: {e.returncode}")
            logger.error(f"STDOUT:\n{e.stdout}")
            logger.error(f"STDERR:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during shared library compilation: {e}")
            return False
    


if __name__ == '__main__':
    # Example usage:
    cjson_config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON.yaml"
    logger.info(f"Attempting to compile library using config: {cjson_config_path}")
    
    try:
        handler = LibraryHandler(cjson_config_path)
        # if handler.compile_shared_library():
        if handler.compile_static_library():
            logger.info("Library compilation process completed successfully.")
        else:
            logger.error("Library compilation process failed.")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Initialization failed: {e}")