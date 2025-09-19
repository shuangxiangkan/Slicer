#!/usr/bin/env python3
"""
Simplified logging tool module
"""

import sys

class Colors:
    """ANSI color codes"""
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

class Logger:
    """Simplified colored logger"""
    
    def __init__(self, enable_colors: bool = True):
        self.enable_colors = enable_colors
    
    def _log(self, color: str, symbol: str, level: str, message: str, file=None):
        """Internal logging method"""
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
    
   

# Create global logger instance
logger = Logger()

# 4 core logging functions
def log_info(message: str):
    logger.info(message)

def log_success(message: str):
    logger.success(message)

def log_warning(message: str):
    logger.warning(message)

def log_error(message: str):
    logger.error(message)