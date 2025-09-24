#!/usr/bin/env python3
"""
编译工具类 - 为harness生成提供编译验证功能
提供CompileUtils类用于在harness生成过程中进行编译验证
"""

import subprocess
import tempfile
from pathlib import Path
from log import *

class CompileUtils:
    """通用编译工具类"""
    
    def __init__(self, config_parser=None):
        """
        初始化编译工具
        
        Args:
            config_parser: 配置解析器实例
        """
        self.config_parser = config_parser
        
        # 获取编译配置
        if self.config_parser:
            self.driver_config = self.config_parser.get_driver_build_config()
            self.header_paths = self.config_parser.get_header_file_paths()
            self.library_path = self.config_parser.get_library_file_path("static")
        else:
            self.driver_config = None
            self.header_paths = []
            self.library_path = None
    
    def build_compile_command(self, harness_file, output_binary):
        """
        构建编译命令
        
        Args:
            harness_file: 源文件路径
            output_binary: 输出二进制文件路径
            
        Returns:
            list: 编译命令列表
        """
        # 获取编译器
        if self.driver_config and self.driver_config['compiler']:
            compiler = self.driver_config['compiler'][0]
        else:
            compiler = 'afl-clang-fast++'
        
        # 基础编译命令
        compile_cmd = [
            compiler,
            '-o', str(output_binary),
            str(harness_file)
        ]
        
        # 添加头文件路径
        for header_path in self.header_paths:
            header_dir = str(Path(header_path).parent)
            if header_dir not in ['-I' + arg for arg in compile_cmd if arg.startswith('-I')]:
                compile_cmd.extend(['-I', header_dir])
        
        # 添加库文件路径
        if self.library_path:
            compile_cmd.append(str(self.library_path))
        
        # 添加额外的flags
        if self.driver_config and self.driver_config['extra_flags']:
            compile_cmd.extend(self.driver_config['extra_flags'])
        
        # 添加默认编译选项
        default_flags = [
            '-g',  # 调试信息
            '-O0', # 无优化，便于调试和覆盖率统计
            '-fsanitize=address',  # AddressSanitizer
        ]
        
        # 如果是AFL++编译器，添加覆盖率插桩
        if 'afl-clang' in compiler:
            default_flags.append('-fsanitize-coverage=trace-pc-guard')
        
        compile_cmd.extend(default_flags)
        
        return compile_cmd
    
    def compile_harness_in_temp(self, source_file, purpose="testing"):
        """
        在临时目录编译harness
        
        Args:
            source_file: 源文件路径
            purpose: 编译目的（用于日志和临时目录命名）
            
        Returns:
            tuple: (success: bool, binary_path: Path, temp_dir: Path)
        """
        source_name = Path(source_file).name
        log_info(f"在临时目录编译harness用于{purpose}: {source_name}")
        
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp(prefix=f"harness_{purpose}_"))
        output_binary = temp_dir / f"{Path(source_file).stem}_compiled"
        
        try:
            # 构建编译命令
            compile_cmd = self.build_compile_command(source_file, output_binary)
            
            log_info(f"编译命令: {' '.join(compile_cmd)}")
            
            result = subprocess.run(
                compile_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                log_success(f"临时编译成功: {source_name}")
                return True, output_binary, temp_dir
            else:
                log_error(f"临时编译失败 [{source_name}]: {result.stderr}")
                # 清理临时目录
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, None
                
        except subprocess.TimeoutExpired:
            log_error(f"临时编译超时 [{source_name}]")
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, None
        except Exception as e:
            log_error(f"临时编译异常 [{source_name}]: {str(e)}")
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, None
    

# 便捷函数
def create_compile_utils(config_parser=None):
    """创建编译工具实例"""
    return CompileUtils(config_parser)

# CompileFilter class and compile_filter function have been removed
# as compilation verification is now integrated into the harness generation process.
# Only CompileUtils is retained for use in harness_generator.py

def main():
    """命令行入口（已弃用，保持兼容性）"""
    import sys
    log_error("该命令行接口已弃用。编译验证现在集成在harness生成过程中。")
    log_error("请使用 harness_generator.py 或 main.py 进行harness生成和验证。")
    sys.exit(1)

if __name__ == "__main__":
    main()