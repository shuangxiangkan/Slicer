#!/usr/bin/env python3
"""
日志工具模块
提供带颜色的日志输出功能，用于替换print语句
"""

import sys
from enum import Enum
from typing import Optional

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Colors:
    """ANSI颜色代码"""
    # 基础颜色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 亮色
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # 样式
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    # 重置
    RESET = '\033[0m'
    
    # 背景色
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'

class Logger:
    """彩色日志记录器"""
    
    def __init__(self, enable_colors: bool = True):
        self.enable_colors = enable_colors
        self.level_colors = {
            LogLevel.DEBUG: Colors.BRIGHT_BLACK,
            LogLevel.INFO: Colors.CYAN,
            LogLevel.SUCCESS: Colors.GREEN,
            LogLevel.WARNING: Colors.YELLOW,
            LogLevel.ERROR: Colors.RED,
            LogLevel.CRITICAL: Colors.BRIGHT_RED + Colors.BOLD
        }
        self.level_symbols = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ📪",
            LogLevel.SUCCESS: "✅",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🚨"
        }
    
    def _format_message(self, level: LogLevel, message: str, prefix: str = "") -> str:
        """格式化日志消息"""
        if not self.enable_colors:
            symbol = self.level_symbols.get(level, "")
            return f"{symbol} [{level.value}] {prefix}{message}"
        
        color = self.level_colors.get(level, Colors.WHITE)
        symbol = self.level_symbols.get(level, "")
        
        formatted = f"{color}{symbol} [{level.value}]{Colors.RESET} {prefix}{message}"
        return formatted
    
    def _log(self, level: LogLevel, message: str, prefix: str = "", file=None):
        """内部日志方法"""
        if file is None:
            file = sys.stdout if level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.SUCCESS] else sys.stderr
        
        formatted_message = self._format_message(level, message, prefix)
        print(formatted_message, file=file)
    
    def debug(self, message: str, prefix: str = ""):
        """调试信息"""
        self._log(LogLevel.DEBUG, message, prefix)
    
    def info(self, message: str, prefix: str = ""):
        """一般信息"""
        self._log(LogLevel.INFO, message, prefix)
    
    def success(self, message: str, prefix: str = ""):
        """成功信息"""
        self._log(LogLevel.SUCCESS, message, prefix)
    
    def warning(self, message: str, prefix: str = ""):
        """警告信息"""
        self._log(LogLevel.WARNING, message, prefix)
    
    def error(self, message: str, prefix: str = ""):
        """错误信息"""
        self._log(LogLevel.ERROR, message, prefix)
    
    def critical(self, message: str, prefix: str = ""):
        """严重错误信息"""
        self._log(LogLevel.CRITICAL, message, prefix)
    
    def step(self, message: str, step_num: Optional[int] = None):
        """步骤信息（带特殊格式）"""
        if step_num:
            prefix = f"🔧 第{step_num}步："
        else:
            prefix = "🔧 "
        self.info(message, prefix)
    
    def section(self, message: str, char: str = "=", width: int = 60):
        """章节分隔符"""
        separator = char * width
        self.info(separator)
        self.info(message)
        self.info(separator)
    
    def subsection(self, message: str, char: str = "-", width: int = 40):
        """子章节分隔符"""
        separator = char * width
        self.info(separator)
        self.info(message)
    
    def progress(self, current: int, total: int, message: str = ""):
        """进度信息"""
        percentage = (current / total) * 100 if total > 0 else 0
        progress_msg = f"进度: {current}/{total} ({percentage:.1f}%)"
        if message:
            progress_msg += f" - {message}"
        self.info(progress_msg, "📊 ")
    
    def result(self, success_count: int, total_count: int, operation: str = "操作"):
        """结果汇总"""
        failed_count = total_count - success_count
        if failed_count == 0:
            self.success(f"{operation}完成: 总数{total_count}, 全部成功")
        else:
            self.warning(f"{operation}完成: 总数{total_count}, 成功{success_count}, 失败{failed_count}")

# 创建全局日志实例
logger = Logger()

# 便捷函数
def log_debug(message: str, prefix: str = ""):
    """调试日志"""
    logger.debug(message, prefix)

def log_info(message: str, prefix: str = ""):
    """信息日志"""
    logger.info(message, prefix)

def log_success(message: str, prefix: str = ""):
    """成功日志"""
    logger.success(message, prefix)

def log_warning(message: str, prefix: str = ""):
    """警告日志"""
    logger.warning(message, prefix)

def log_error(message: str, prefix: str = ""):
    """错误日志"""
    logger.error(message, prefix)

def log_critical(message: str, prefix: str = ""):
    """严重错误日志"""
    logger.critical(message, prefix)

def log_step(message: str, step_num: Optional[int] = None):
    """步骤日志"""
    logger.step(message, step_num)

def log_section(message: str, char: str = "=", width: int = 60):
    """章节日志"""
    logger.section(message, char, width)

def log_subsection(message: str, char: str = "-", width: int = 40):
    """子章节日志"""
    logger.subsection(message, char, width)

def log_progress(current: int, total: int, message: str = ""):
    """进度日志"""
    logger.progress(current, total, message)

def log_result(success_count: int, total_count: int, operation: str = "操作"):
    """结果日志"""
    logger.result(success_count, total_count, operation)

# AFL++相关的特殊日志函数
def log_afl_error(message: str):
    """AFL++错误（严重错误，红色）"""
    logger.critical(f"AFL++错误: {message}")

def log_afl_warning(message: str):
    """AFL++警告（黄色）"""
    logger.warning(f"AFL++警告: {message}")

def log_afl_success(message: str):
    """AFL++成功（绿色）"""
    logger.success(f"AFL++: {message}")

def log_afl(message: str):
    """AFL++一般信息（蓝色）"""
    logger.info(f"AFL++: {message}")

def log_coverage(message: str):
    """覆盖率分析信息（青色）"""
    logger.info(f"覆盖率: {message}", prefix="📊")

def log_compile_error(harness_name: str, error_msg: str):
    """编译错误"""
    logger.error(f"编译失败 [{harness_name}]: {error_msg}")

def log_compile_success(harness_name: str):
    """编译成功"""
    logger.success(f"编译成功: {harness_name}")

def log_execution_error(harness_name: str, error_msg: str):
    """执行错误"""
    logger.error(f"执行失败 [{harness_name}]: {error_msg}")

def log_execution_success(harness_name: str):
    """执行成功"""
    logger.success(f"执行成功: {harness_name}")

def log_coverage_analysis(harness_name: str, quality: str, score: float = 0):
    """覆盖率分析结果"""
    if quality == 'good':
        logger.success(f"质量评估 [{harness_name}]: {quality} (分数: {score:.2f})")
    elif quality in ['no_new_coverage', 'poor_coverage_growth']:
        logger.warning(f"质量评估 [{harness_name}]: {quality} (分数: {score:.2f})")
    else:
        logger.error(f"质量评估 [{harness_name}]: {quality} (分数: {score:.2f})")

if __name__ == "__main__":
    # 测试日志功能
    log_section("日志功能测试")
    log_debug("这是调试信息")
    log_info("这是一般信息")
    log_success("这是成功信息")
    log_warning("这是警告信息")
    log_error("这是错误信息")
    log_critical("这是严重错误信息")
    
    log_subsection("AFL++相关日志测试")
    log_afl_success("AFL++工具可用")
    log_afl_warning("AFL++配置可能有问题")
    log_afl_error("AFL++不可用，请确保已安装AFL++并在PATH中")
    
    log_subsection("进度和结果测试")
    log_progress(3, 10, "处理harness文件")
    log_result(8, 10, "编译")