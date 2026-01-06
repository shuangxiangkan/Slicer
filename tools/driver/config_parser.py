#!/usr/bin/env python3
"""
Configuration file parser
For parsing YAML configuration files of fuzzing libraries
"""

import yaml
import os
import sys
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
        compiler_required = ['CC_FUZZ', 'CXX_FUZZ']
        for field in compiler_required:
            if field not in self._config_data['compiler']:
                raise ValueError(f"Missing required compiler configuration field: {field}")
        
        # Validate driver_build configuration (optional but if present, must have required fields)
        if 'driver_build' in self._config_data:
            driver_build = self._config_data['driver_build']
            driver_required = ['compiler', 'extra_flags']
            for field in driver_required:
                if field not in driver_build:
                    raise ValueError(f"Missing required driver_build field: {field}")
            
            # Validate that compiler field is not empty
            if not driver_build['compiler'] or not any(c.strip() for c in driver_build['compiler']):
                raise ValueError("driver_build.compiler must contain at least one non-empty compiler specification")
    
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
            'cxx_fuzz': comp_data['CXX_FUZZ']
        }
    
    def get_headers(self) -> List[str]:
        """Get header files list (for API extraction and source analysis)
        
        Returns:
            List of header file paths relative to library directory
        """
        return self._config_data.get('headers', [])
    
    def get_header_include(self) -> List[str]:
        """Get header file names for #include statements in harness
        
        Returns:
            List of header file names (without path) for #include directives
        """
        return self._config_data.get('header_include', [])
    
    def get_header_folder(self) -> List[str]:
        """Get header folder paths for compilation
        
        Returns:
            List of header folder paths relative to library directory for -I flags
        """
        return self._config_data.get('header_folder', [])
    
    def get_library_name(self) -> str:
        """Get library name"""
        return self._config_data['library']['name']
    
    def get_include_headers(self) -> List[str]:
        """Get include headers for fuzz harness (backward compatibility)
        
        Returns:
            List of header file names for #include directives
        """
        # 优先使用新的header_include字段，如果不存在则回退到headers字段
        header_include = self.get_header_include()
        if header_include:
            return header_include
        
        # 向后兼容：从headers字段提取文件名
        headers = self.get_headers()
        return [header.split('/')[-1] if '/' in header else header for header in headers]
    
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
    
    def get_driver_build_config(self) -> Optional[Dict[str, List[str]]]:
        """Get driver build configuration
        
        Returns:
            Dictionary containing compiler and extra_flags lists
            Returns None if driver_build section is not found
        """
        if 'driver_build' not in self._config_data:
            return None
        
        driver_data = self._config_data['driver_build']
        
        # Format compiler values to replace placeholders
        compiler_list = driver_data.get('compiler', [])
        formatted_compilers = []
        for compiler in compiler_list:
            if compiler.strip():  # Skip empty strings
                formatted_compilers.append(self.format_command(compiler))
        
        # Format extra_flags to replace placeholders
        extra_flags_list = driver_data.get('extra_flags', [])
        formatted_extra_flags = []
        for flag in extra_flags_list:
            if flag.strip():  # Skip empty strings
                formatted_extra_flags.append(self.format_command(flag))
        
        return {
             'compiler': formatted_compilers,
             'extra_flags': formatted_extra_flags
         }
    
    def get_api_selection(self) -> Dict[str, List[str]]:
        """Get API selection configuration"""
        api_data = self._config_data['api_selection']
        return {
            'api_prefix': api_data.get('api_prefix', []),
            'api_macros': api_data.get('api_macros', []),
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
    
    def get_fuzzing_config(self) -> Optional[Dict[str, str]]:
        """Get fuzzing configuration (optional)"""
        if 'fuzzing' not in self._config_data:
            return None
        
        fuzzing_data = self._config_data['fuzzing']
        return {
            'seeds_dir': fuzzing_data.get('seeds_dir', ''),
            'dictionary_file': fuzzing_data.get('dictionary_file', '')
        }
    
    def get_seeds_dir(self) -> Optional[str]:
        """Get seeds directory path"""
        fuzzing_config = self.get_fuzzing_config()
        if fuzzing_config and fuzzing_config['seeds_dir']:
            return fuzzing_config['seeds_dir']
        return None
    
    def get_dictionary_file(self) -> Optional[str]:
        """Get dictionary file path"""
        fuzzing_config = self.get_fuzzing_config()
        if fuzzing_config and fuzzing_config['dictionary_file']:
            return fuzzing_config['dictionary_file']
        return None
    
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
        """Get absolute paths of header files (backward compatibility)
        
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

    def get_compilation_header_file_paths(self) -> List[str]:
        """Get absolute paths of header files for compilation verification
        
        This method correctly uses header_include + header_folder fields
        instead of the headers field which is used for API extraction.
        
        Returns:
            List of absolute paths to header files that should exist for compilation
        """
        header_includes = self.get_header_include()
        header_folders = self.get_header_folder()
        library_dir = self.get_target_library_dir()
        
        header_paths = []
        
        # Combine each header_include with each header_folder
        for header_folder in header_folders:
            for header_include in header_includes:
                if os.path.isabs(header_folder):
                    folder_path = header_folder
                else:
                    # Relative to library directory
                    folder_path = os.path.join(library_dir, header_folder)
                
                # Combine folder path with header file name
                header_path = os.path.join(folder_path, header_include)
                header_paths.append(os.path.abspath(header_path))
        
        return header_paths
    
    def get_header_folder_paths(self) -> List[str]:
        """Get absolute paths of header folders for compilation
        
        Returns:
            List of absolute paths to header folders for -I flags
        """
        header_folders = self.get_header_folder()
        library_dir = self.get_target_library_dir()
        
        folder_paths = []
        for folder in header_folders:
            if os.path.isabs(folder):
                folder_paths.append(folder)
            else:
                # 相对于库目录的路径
                folder_path = os.path.join(library_dir, folder)
                folder_paths.append(os.path.abspath(folder_path))
        
        return folder_paths
    
    def get_expanded_header_file_paths(self) -> List[str]:
        """Get expanded absolute paths of header files for API extraction
        
        This method expands wildcard patterns in the headers field to actual file paths.
        
        Returns:
            List of absolute paths to header files (expanded from wildcards)
        """
        import glob
        
        header_files = self.get_headers()
        library_dir = self.get_target_library_dir()
        
        expanded_paths = []
        
        for header_file in header_files:
            # 构建完整路径
            if os.path.isabs(header_file):
                full_path = header_file
            else:
                full_path = os.path.join(library_dir, header_file)
            
            # 检查是否包含通配符
            if '*' in header_file or '?' in header_file:
                # 使用glob解析通配符
                matched_files = glob.glob(full_path, recursive=True)
                for matched_file in matched_files:
                    if os.path.isfile(matched_file) and matched_file.endswith('.h'):
                        expanded_paths.append(os.path.abspath(matched_file))
            elif os.path.isdir(full_path):
                # 如果是目录，查找其中的所有头文件
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        if file.endswith('.h'):
                            file_path = os.path.join(root, file)
                            expanded_paths.append(os.path.abspath(file_path))
            elif os.path.isfile(full_path):
                # 如果是单个文件且是头文件
                if full_path.endswith('.h'):
                    expanded_paths.append(os.path.abspath(full_path))
        
        return expanded_paths
    
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
    
    config_path = "/home/shuangxiang/workspace/code/Slicer/tools/driver/configs/cJSON/cJSON.yaml"
    
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
        print(f"API Prefix: {api_selection['api_prefix']}")
        print(f"API Macros: {api_selection['api_macros']}")
        print(f"Exclude: {api_selection['exclude']}")
        
        # Display documentation configuration
        doc_config = parser.get_documentation_config()
        if doc_config:
            print(f"\n=== Documentation Configuration ===")
            print(f"Target Files: {doc_config['target_files']}")
        
        # Test driver build configuration
        print(f"\n=== Driver Build Configuration ===")
        driver_config = parser.get_driver_build_config()
        if driver_config:
            print(f"Compiler: {driver_config['compiler']}")
            print(f"Extra Flags: {driver_config['extra_flags']}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)