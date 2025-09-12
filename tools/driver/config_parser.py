#!/usr/bin/env python3
"""
Configuration file parser
For parsing YAML configuration files of fuzzing libraries
"""

import yaml
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

class ConfigParser:
    """Configuration file parser"""
    
    def __init__(self, config_path: str, base_dir: Optional[str] = None):
        """
        Initialize configuration parser
        
        Args:
            config_path: Configuration file path
            base_dir: Base directory path, defaults to config_parser.py file's directory
        """
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Set base directory
        if base_dir is None:
            # Default to config_parser.py file's directory
            self.base_dir = Path(__file__).parent
        else:
            self.base_dir = Path(base_dir)
        
        self._config_data = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}")
        except Exception as e:
            raise RuntimeError(f"Configuration file loading failed: {e}")
    
    def _validate_config(self):
        """Validate required fields in configuration file"""
        required_sections = ['library', 'compiler', 'headers', 'source_dirs', 'static_build', 'api_selection']
        
        for section in required_sections:
            if section not in self._config_data:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate library information
        lib_required = ['name', 'version', 'repo_url', 'language']
        for field in lib_required:
            if field not in self._config_data['library']:
                raise ValueError(f"Missing required library information field: {field}")
        
        # Validate compiler configuration
        compiler_required = ['CC_FUZZ', 'CXX_FUZZ', 'CFLAGS_ASAN', 'CXXFLAGS_ASAN']
        for field in compiler_required:
            if field not in self._config_data['compiler']:
                raise ValueError(f"Missing required compiler configuration field: {field}")
    
    def get_library_info(self) -> Dict[str, str]:
        """Get library information"""
        lib_data = self._config_data['library']
        return {
            'name': lib_data['name'],
            'version': lib_data['version'],
            'repo_url': lib_data['repo_url'],
            'language': lib_data['language']
        }
    
    def get_compiler_config(self) -> Dict[str, str]:
        """Get compiler configuration"""
        comp_data = self._config_data['compiler']
        return {
            'cc_fuzz': comp_data['CC_FUZZ'],
            'cxx_fuzz': comp_data['CXX_FUZZ'],
            'cflags_asan': comp_data['CFLAGS_ASAN'],
            'cxxflags_asan': comp_data['CXXFLAGS_ASAN']
        }
    
    def get_headers(self) -> List[str]:
        """Get header files list"""
        return self._config_data.get('headers', [])
    
    def get_library_name(self) -> str:
        """Get library name"""
        return self._config_data['library']['name']
    
    def get_include_headers(self) -> List[str]:
        """Get include headers for fuzz harness"""
        return self.get_headers()
    
    def get_source_dirs(self) -> List[str]:
        """Get source directories list"""
        return self._config_data.get('source_dirs', [])
    
    def get_exclude_dirs(self) -> List[str]:
        """Get exclude directory list"""
        exclude_dirs = self._config_data.get('exclude_dirs', [])
        # Filter empty strings
        return [d for d in exclude_dirs if d.strip()]
    
    def get_static_build_config(self) -> Dict[str, str]:
        """Get static library build configuration"""
        build_data = self._config_data['static_build']
        return {
            'output': build_data['output'],
            'command': build_data['command'],
            'static_lib_name': build_data.get('static_lib_name', '')
        }
    
    def get_shared_build_config(self) -> Optional[Dict[str, str]]:
        """Get shared library build configuration (optional)"""
        if 'shared_build' not in self._config_data:
            return None
        
        build_data = self._config_data['shared_build']
        return {
            'output': build_data['output'],
            'command': build_data['command'],
            'shared_lib_name': build_data.get('shared_lib_name', '')
        }
    
    def get_static_driver_build_command(self) -> str:
        """Get static library driver build command"""
        return self._config_data.get('static_driver_build', '')
    
    def get_shared_driver_build_command(self) -> Optional[str]:
        """Get shared library driver build command (optional)"""
        return self._config_data.get('shared_driver_build')
    
    def get_api_selection(self) -> Dict[str, List[str]]:
        """Get API selection configuration"""
        api_data = self._config_data['api_selection']
        return {
            'include_prefix': api_data.get('include_prefix', []),
            'keywords': api_data.get('keywords', []),
            'exclude': api_data.get('exclude', [])
        }
    
    def get_documentation_config(self) -> Optional[Dict[str, List[str]]]:
        """Get documentation configuration (optional)"""
        if 'documentation' not in self._config_data:
            return None
        
        doc_data = self._config_data['documentation']
        return {
            'target_files': doc_data.get('target_files', [])
        }
    
    def format_command(self, command_template: str, **kwargs) -> str:
        """
        Format command template, replace placeholders
        
        Args:
            command_template: Command template string
            **kwargs: Additional replacement parameters
        
        Returns:
            Formatted command string
        """
        # Get basic configuration information
        lib_info = self.get_library_info()
        compiler_config = self.get_compiler_config()
        static_build = self.get_static_build_config()
        shared_build = self.get_shared_build_config()
        
        # Build replacement dictionary
        format_dict = {
            'repo_url': lib_info['repo_url'],
            'CC_FUZZ': compiler_config['cc_fuzz'],
            'CXX_FUZZ': compiler_config['cxx_fuzz'],
            'CFLAGS_ASAN': compiler_config['cflags_asan'],
            'CXXFLAGS_ASAN': compiler_config['cxxflags_asan'],
            'static_lib_name': static_build['static_lib_name'],
            'shared_lib_name': shared_build['shared_lib_name'] if shared_build else '',
        }
        
        # Add additional parameters
        format_dict.update(kwargs)
        
        try:
            return command_template.format(**format_dict)
        except KeyError as e:
            raise ValueError(f"Command template contains undefined placeholder: {e}")
    
    def get_formatted_static_build_command(self) -> str:
        """Get formatted static library build command"""
        build_config = self.get_static_build_config()
        return self.format_command(build_config['command'])
    
    def get_formatted_shared_build_command(self) -> Optional[str]:
        """Get formatted shared library build command"""
        build_config = self.get_shared_build_config()
        if build_config is None:
            return None
        return self.format_command(build_config['command'])
    
    def get_formatted_static_driver_command(self, driver_path: str, output_path: str) -> str:
        """Get formatted static library driver build command"""
        command_template = self.get_static_driver_build_command()
        return self.format_command(command_template, driver=driver_path, output=output_path)
    
    def get_formatted_shared_driver_command(self, driver_path: str, output_path: str) -> Optional[str]:
        """Get formatted shared library driver build command"""
        command_template = self.get_shared_driver_build_command()
        if command_template is None:
            return None
        return self.format_command(command_template, driver=driver_path, output=output_path)
    
    def get_libraries_dir(self) -> str:
        """Get Libraries directory path (where all libraries are downloaded)
            
        Returns:
            Libraries directory path
        """
        libraries_dir = self.base_dir / "Libraries"
        libraries_dir.mkdir(exist_ok=True)
        return str(libraries_dir)
    
    def get_target_library_dir(self) -> str:
        """Get target library directory path (specific library being analyzed)
            
        Returns:
            Target library directory path
        """
        libraries_base_dir = self.get_libraries_dir()
        library_name = self.get_library_info()['name']
        return str(Path(libraries_base_dir) / library_name)
    
    def get_output_dir(self) -> str:
        """Get Output directory path for the library
            
        Returns:
            Library-specific output directory path
        """
        library_name = self.get_library_info()['name']
        output_dir = self.base_dir / "Output" / library_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)
    
    def get_header_file_paths(self) -> List[str]:
        """Get absolute paths of header files
        
        Returns:
            List of absolute paths to header files
        """
        header_files = self.get_headers()
        library_dir = self.get_target_library_dir()
        
        header_paths = []
        for header_file in header_files:
            if os.path.isabs(header_file):
                header_paths.append(header_file)
            else:
                # 直接按照配置文件中的路径，相对于库目录
                header_path = os.path.join(library_dir, header_file)
                header_paths.append(os.path.abspath(header_path))
        
        return header_paths
    
    def get_library_file_path(self, library_type: str = "static") -> str:
        """Get absolute path of compiled library file
        
        Args:
            library_type: Type of library ("static" or "shared")
            
        Returns:
            Absolute path to the library file
        """
        if library_type == "static":
            build_config = self.get_static_build_config()
        elif library_type == "shared":
            build_config = self.get_shared_build_config()
            if build_config is None:
                raise ValueError(f"Shared library build configuration not found")
        else:
            raise ValueError(f"Invalid library type: {library_type}")
        
        formatted_output = self.format_command(build_config['output'])
        library_dir = self.get_target_library_dir()
        library_path = os.path.join(library_dir, formatted_output)
        return os.path.abspath(library_path)
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Get raw configuration data"""
        return self._config_data.copy()
    
    def __str__(self) -> str:
        """String representation"""
        lib_info = self.get_library_info()
        return f"ConfigParser({lib_info['name']} v{lib_info['version']})"
    
    def __repr__(self) -> str:
        """Detailed string representation"""
        return f"ConfigParser(config_path='{self.config_path}')"


def load_config(config_path: str) -> ConfigParser:
    """
    Convenience function: load configuration file
    
    Args:
        config_path: Configuration file path
    
    Returns:
        ConfigParser instance
    """
    return ConfigParser(config_path)


if __name__ == "__main__":
    
    config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON.yaml"
    
    try:
        # Load configuration
        parser = load_config(config_path)
        
        # Display library information
        lib_info = parser.get_library_info()
        print(f"\n=== Library Information ===")
        print(f"Name: {lib_info['name']}")
        print(f"Version: {lib_info['version']}")
        print(f"Repository: {lib_info['repo_url']}")
        print(f"Language: {lib_info['language']}")
        
        # Display compiler configuration
        compiler = parser.get_compiler_config()
        print(f"\n=== Compiler Configuration ===")
        print(f"C Compiler: {compiler['cc_fuzz']}")
        print(f"C++ Compiler: {compiler['cxx_fuzz']}")
        print(f"C Flags: {compiler['cflags_asan']}")
        print(f"C++ Flags: {compiler['cxxflags_asan']}")
        
        # Display file configuration
        print(f"\n=== File Configuration ===")
        print(f"Headers: {parser.get_headers()}")
        print(f"Source Directories: {parser.get_source_dirs()}")
        print(f"Exclude Directories: {parser.get_exclude_dirs()}")
        
        # Display build configuration
        static_build = parser.get_static_build_config()
        print(f"\n=== Static Library Build ===")
        print(f"Static Library Name: {static_build['static_lib_name']}")
        print(f"Output: {static_build['output']}")
        print(f"Command: {parser.get_formatted_static_build_command()}")
        
        shared_build = parser.get_shared_build_config()
        if shared_build:
            print(f"\n=== Shared Library Build ===")
            print(f"Shared Library Name: {shared_build['shared_lib_name']}")
            print(f"Output: {shared_build['output']}")
            print(f"Command: {parser.get_formatted_shared_build_command()}")
        
        # Display API selection
        api_selection = parser.get_api_selection()
        print(f"\n=== API Selection ===")
        print(f"Include Prefix: {api_selection['include_prefix']}")
        print(f"Keywords: {api_selection['keywords']}")
        print(f"Exclude: {api_selection['exclude']}")
        
        # Display documentation configuration
        doc_config = parser.get_documentation_config()
        if doc_config:
            print(f"\n=== Documentation Configuration ===")
            print(f"Target Files: {doc_config['target_files']}")
        
        # Test driver build commands
        print(f"\n=== Driver Build Commands ===")
        static_driver_cmd = parser.get_formatted_static_driver_command("test_driver.c", "test_driver")
        print(f"Static Library Driver: {static_driver_cmd}")
        
        shared_driver_cmd = parser.get_formatted_shared_driver_command("test_driver.c", "test_driver")
        if shared_driver_cmd:
            print(f"Shared Library Driver: {shared_driver_cmd}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)