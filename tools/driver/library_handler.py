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

    def __init__(self, config_parser: ConfigParser):
        """
        Initializes the LibraryHandler with a configuration parser.

        Args:
            config_parser: ConfigParser object with loaded configuration.
        """
        self.config_parser = config_parser
        self.library_name = self.config_parser.get_library_info()['name']
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.libs_dir = os.path.join(self.base_dir, "libraries")
        os.makedirs(self.libs_dir, exist_ok=True)

    def compile_library(self, library_type: str = "static") -> bool:
        """
        Compiles the library based on the configuration and type.

        Args:
            library_type: Type of library to compile ("static" or "shared"). Defaults to "static".

        Returns:
            True if compilation is successful, False otherwise.
        """
        if library_type not in ["static", "shared"]:
            logger.error(f"Invalid library type: {library_type}. Must be 'static' or 'shared'.")
            return False
            
        logger.info(f"Starting {library_type} library compilation for {self.library_name}...")
        
        # Get build configuration and command based on type
        if library_type == "static":
            build_config = self.config_parser.get_static_build_config()
            build_command = self.config_parser.get_formatted_static_build_command()
        else:  # shared
            build_config = self.config_parser.get_shared_build_config()
            if build_config is None:
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
            logger.info(f"{library_type.capitalize()} library compilation successful for {self.library_name}.")
            logger.info(f"STDOUT:\n{result.stdout}")
            logger.info(f"{library_type.capitalize()} library compilation completed successfully.")
            
            # 检查AFL++插桩
            formatted_output = self.config_parser.format_command(build_config['output'])
            library_path = os.path.join(self.libs_dir, formatted_output)
            
            if os.path.exists(library_path):
                if check_afl_instrumentation(library_path):
                    logger.info(f"AFL++ instrumentation verified successfully for {library_path}")
                else:
                    logger.error(f"AFL++ instrumentation verification failed for {library_path}")
                    return False
            else:
                logger.error(f"{library_type.capitalize()} library file not found at expected path: {library_path}")
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"{library_type.capitalize()} library compilation failed for {self.library_name}.")
            logger.error(f"Return code: {e.returncode}")
            logger.error(f"STDOUT:\n{e.stdout}")
            logger.error(f"STDERR:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred during {library_type} library compilation: {e}")
            return False


if __name__ == '__main__':
    # Example usage:
    cjson_config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON.yaml"
    logger.info(f"Attempting to compile library using config: {cjson_config_path}")
    
    try:
        config_parser = ConfigParser(cjson_config_path)
        handler = LibraryHandler(config_parser)
        if handler.compile_library("shared"):
        # if handler.compile_library("static"):
            logger.info("Library compilation process completed successfully.")
        else:
            logger.error("Library compilation process failed.")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Initialization failed: {e}")