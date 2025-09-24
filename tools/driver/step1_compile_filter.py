#!/usr/bin/env python3
"""
三步筛选流程演示 - 第一步：编译筛选
模拟 CompileHarness.checkSequence 和 compileHarness 方法的编译阶段
"""

import subprocess
import json
import shutil
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
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, None, None
                
        except subprocess.TimeoutExpired:
            log_error(f"临时编译超时 [{source_name}]")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, None
        except Exception as e:
            log_error(f"临时编译异常 [{source_name}]: {str(e)}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, None, None
    

# 便捷函数
def create_compile_utils(config_parser=None):
    """创建编译工具实例"""
    return CompileUtils(config_parser)

class CompileFilter:
    def __init__(self, harness_dir, log_dir, next_stage_dir=None, config_parser=None):
        self.harness_dir = Path(harness_dir)
        self.log_dir = Path(log_dir)
        self.next_stage_dir = Path(next_stage_dir) if next_stage_dir else None
        self.config_parser = config_parser
        self.compile_stats = {
            'total': 0,
            'compile_success': 0,
            'compile_failed': 0,
            'failed_harnesses': []
        }
        
        # 创建编译工具
        self.compile_utils = create_compile_utils(config_parser)
    
    def compile_harness(self, harness_file):
        """编译单个harness文件（验证编译可行性，自动清理临时文件）"""
        success, binary_path, temp_dir = self.compile_utils.compile_harness_in_temp(harness_file, "verification")
        
        # 立即清理临时目录，因为Step1只需要验证编译可行性
        if temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                log_info(f"清理编译验证临时目录: {temp_dir}")
            except:
                pass
        
        if success:
            self.compile_stats['compile_success'] += 1
            return True, "Compilation successful"
        else:
            self.compile_stats['compile_failed'] += 1
            self.compile_stats['failed_harnesses'].append({
                'file': harness_file.name,
                'error': 'Compilation failed'
            })
            return False, "Compilation failed"
    
    def filter_harnesses(self):
        """筛选所有harness文件"""
        log_info("三步筛选流程 - 第一步：编译筛选")
        log_info(f"扫描目录: {self.harness_dir}")
        
        # 获取所有C/C++文件
        harness_files = list(self.harness_dir.glob("*.c")) + list(self.harness_dir.glob("*.cpp"))
        self.compile_stats['total'] = len(harness_files)
        
        if not harness_files:
            log_warning("未找到任何C/C++文件")
            return []
        
        log_info(f"找到 {len(harness_files)} 个harness文件")
        
        successful_harnesses = []
        
        # 创建下一阶段目录
        if self.next_stage_dir:
            self.next_stage_dir.mkdir(parents=True, exist_ok=True)
        
        for harness_file in harness_files:
            success, output = self.compile_harness(harness_file)
            if success:
                # 只保存源文件信息，不再维护binary路径
                harness_info = {
                    'source': str(harness_file),
                    'compile_output': output
                }
                successful_harnesses.append(harness_info)
                
                # 复制成功编译的源文件到下一阶段目录
                if self.next_stage_dir:
                    dest_file = self.next_stage_dir / harness_file.name
                    shutil.copy2(harness_file, dest_file)
                    log_info(f"已复制到下一阶段: {dest_file}")
        
        # 保存编译统计信息
        self.save_compile_stats()
        
        log_info("编译筛选完成")
        failed_count = self.compile_stats['total'] - self.compile_stats['compile_success']
        if failed_count == 0:
            log_success(f"编译完成: 总数{self.compile_stats['total']}, 全部成功")
        else:
            log_warning(f"编译完成: 总数{self.compile_stats['total']}, 成功{self.compile_stats['compile_success']}, 失败{failed_count}")
        
        return successful_harnesses
    
    def save_compile_stats(self):
        """保存编译统计信息"""
        stats_file = self.log_dir / "step1_compile_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.compile_stats, f, indent=2, ensure_ascii=False)
        log_info(f"编译统计信息已保存到: {stats_file}")

def compile_filter(harness_dir, log_dir, next_stage_dir=None, config_parser=None):
    """编译筛选API接口"""
    # 确保日志目录存在
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建编译筛选器
    filter = CompileFilter(harness_dir, log_dir, next_stage_dir, config_parser)
    
    # 执行筛选
    successful_harnesses = filter.filter_harnesses()
    
    # 保存编译统计摘要（不再保存详细文件列表）
    summary_file = Path(log_dir) / "step1_compile_summary.json"
    summary_data = {
        'total_harnesses': filter.compile_stats['total'],
        'successful_harnesses': filter.compile_stats['compile_success'],
        'failed_harnesses': filter.compile_stats['compile_failed'],
        'success_rate': filter.compile_stats['compile_success'] / max(filter.compile_stats['total'], 1),
        'note': f"成功编译的源文件已复制到: {next_stage_dir}"
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    log_info(f"编译摘要已保存到: {summary_file}")
    log_success(f"通过编译筛选的harness数量: {len(successful_harnesses)}")
    
    return successful_harnesses

def main():
    """命令行入口（保持兼容性）"""
    import sys
    if len(sys.argv) != 3:
        log_error("用法: python step1_compile_filter.py <harness_dir> <log_dir>")
        sys.exit(1)
    
    harness_dir = sys.argv[1]
    log_dir = sys.argv[2]
    
    compile_filter(harness_dir, log_dir)

if __name__ == "__main__":
    main()