#!/usr/bin/env python3
"""
简化的日志工具模块
只保留最常用的5个日志函数
"""

import sys

class Colors:
    """ANSI颜色代码"""
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

class Logger:
    """简化的彩色日志记录器"""
    
    def __init__(self, enable_colors: bool = True):
        self.enable_colors = enable_colors
    
    def _log(self, color: str, symbol: str, level: str, message: str, file=None):
        """内部日志方法"""
        if file is None:
            file = sys.stdout if level in ["INFO", "SUCCESS"] else sys.stderr
        
        if self.enable_colors:
            formatted_message = f"{color}{symbol} [{level}]{Colors.RESET} {message}"
        else:
            formatted_message = f"{symbol} [{level}] {message}"
        
        print(formatted_message, file=file)
    
    def info(self, message: str):
        self._log(Colors.CYAN, "ℹ️", "INFO", message)
    
    def success(self, message: str):
        self._log(Colors.GREEN, "✅", "SUCCESS", message)
    
    def warning(self, message: str):
        self._log(Colors.YELLOW, "⚠️", "WARNING", message)
    
    def error(self, message: str):
        self._log(Colors.RED, "❌", "ERROR", message)
    
   

# 创建全局日志实例
logger = Logger()

# 4个核心日志函数
def log_info(message: str):
    logger.info(message)

def log_success(message: str):
    logger.success(message)

def log_warning(message: str):
    logger.warning(message)

def log_error(message: str):
    logger.error(message)